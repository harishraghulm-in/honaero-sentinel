#include "sentinel/common/process.hpp"
#include <chrono>
#include <iostream>
#include <sstream>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#endif

namespace sentinel {

#if defined(_WIN32)

static std::wstring toWideString(const std::string& str) {
    if (str.empty()) return L"";
    int size = MultiByteToWideChar(CP_UTF8, 0, str.c_str(), -1, nullptr, 0);
    std::wstring wstr(size - 1, 0);
    MultiByteToWideChar(CP_UTF8, 0, str.c_str(), -1, &wstr[0], size);
    return wstr;
}

static std::string escapeWindowsArg(const std::string& arg) {
    if (arg.empty()) return "\"\"";
    bool needsQuotes = false;
    for (char c : arg) {
        if (c == ' ' || c == '\t' || c == '\n' || c == '\v' || c == '\"') {
            needsQuotes = true;
            break;
        }
    }
    if (!needsQuotes) return arg;

    std::string result = "\"";
    for (size_t i = 0; i < arg.length(); ++i) {
        size_t backslashes = 0;
        while (i < arg.length() && arg[i] == '\\') {
            backslashes++;
            i++;
        }
        if (i == arg.length()) {
            result.append(backslashes * 2, '\\');
            break;
        } else if (arg[i] == '\"') {
            result.append(backslashes * 2 + 1, '\\');
            result.push_back('\"');
        } else {
            result.append(backslashes, '\\');
            result.push_back(arg[i]);
        }
    }
    result.push_back('\"');
    return result;
}

ProcessResult ProcessRunner::execute(
    const std::string& executable,
    const std::vector<std::string>& arguments,
    const std::optional<std::string>& working_dir,
    std::chrono::milliseconds timeout)
{
    ProcessResult result;
    auto start_time = std::chrono::steady_clock::now();

    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = nullptr;

    HANDLE outRead, outWrite;
    HANDLE errRead, errWrite;

    if (!CreatePipe(&outRead, &outWrite, &sa, 0)) {
        result.stderr_output = "Failed to create stdout pipe";
        return result;
    }
    SetHandleInformation(outRead, HANDLE_FLAG_INHERIT, 0);

    if (!CreatePipe(&errRead, &errWrite, &sa, 0)) {
        CloseHandle(outRead);
        CloseHandle(outWrite);
        result.stderr_output = "Failed to create stderr pipe";
        return result;
    }
    SetHandleInformation(errRead, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.hStdOutput = outWrite;
    si.hStdError = errWrite;
    si.dwFlags |= STARTF_USESTDHANDLES;

    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    std::string cmdline = escapeWindowsArg(executable);
    for (const auto& arg : arguments) {
        cmdline += " " + escapeWindowsArg(arg);
    }
    std::wstring wcmdline = toWideString(cmdline);
    std::wstring wexe = toWideString(executable);
    std::wstring wdir;
    LPCWSTR pwdir = nullptr;
    if (working_dir.has_value()) {
        wdir = toWideString(*working_dir);
        pwdir = wdir.c_str();
    }

    BOOL created = CreateProcessW(
        wexe.empty() ? nullptr : wexe.c_str(),
        &wcmdline[0],
        nullptr,
        nullptr,
        TRUE,
        0,
        nullptr,
        pwdir,
        &si,
        &pi
    );

    CloseHandle(outWrite);
    CloseHandle(errWrite);

    if (!created) {
        CloseHandle(outRead);
        CloseHandle(errRead);
        result.stderr_output = "CreateProcess failed with error " + std::to_string(GetLastError());
        result.exit_code = -1;
        return result;
    }

    DWORD waitResult = WaitForSingleObject(pi.hProcess, static_cast<DWORD>(timeout.count()));
    if (waitResult == WAIT_TIMEOUT) {
        result.timed_out = true;
        TerminateProcess(pi.hProcess, 1);
        WaitForSingleObject(pi.hProcess, 1000);
    } else {
        DWORD exitCode = 0;
        if (GetExitCodeProcess(pi.hProcess, &exitCode)) {
            result.exit_code = static_cast<int>(exitCode);
        }
    }

    // Read pipes
    char buffer[4096];
    DWORD bytesRead;
    while (ReadFile(outRead, buffer, sizeof(buffer), &bytesRead, nullptr) && bytesRead > 0) {
        result.stdout_output.append(buffer, bytesRead);
    }
    while (ReadFile(errRead, buffer, sizeof(buffer), &bytesRead, nullptr) && bytesRead > 0) {
        result.stderr_output.append(buffer, bytesRead);
    }

    CloseHandle(outRead);
    CloseHandle(errRead);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    auto end_time = std::chrono::steady_clock::now();
    result.duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
    return result;
}

#else

ProcessResult ProcessRunner::execute(
    const std::string& executable,
    const std::vector<std::string>& arguments,
    const std::optional<std::string>& working_dir,
    std::chrono::milliseconds timeout)
{
    ProcessResult result;
    auto start_time = std::chrono::steady_clock::now();

    int outPipe[2];
    int errPipe[2];
    if (pipe(outPipe) != 0 || pipe(errPipe) != 0) {
        result.stderr_output = "Failed to create pipes";
        return result;
    }

    pid_t pid = fork();
    if (pid == 0) {
        // Child
        close(outPipe[0]);
        close(errPipe[0]);
        dup2(outPipe[1], STDOUT_FILENO);
        dup2(errPipe[1], STDERR_FILENO);
        close(outPipe[1]);
        close(errPipe[1]);

        if (working_dir.has_value()) {
            chdir(working_dir->c_str());
        }

        std::vector<char*> argv;
        argv.push_back(const_cast<char*>(executable.c_str()));
        for (const auto& a : arguments) {
            argv.push_back(const_cast<char*>(a.c_str()));
        }
        argv.push_back(nullptr);

        execvp(executable.c_str(), argv.data());
        _exit(127);
    } else if (pid > 0) {
        // Parent
        close(outPipe[1]);
        close(errPipe[1]);

        char buffer[4096];
        ssize_t n;
        while ((n = read(outPipe[0], buffer, sizeof(buffer))) > 0) {
            result.stdout_output.append(buffer, n);
        }
        while ((n = read(errPipe[0], buffer, sizeof(buffer))) > 0) {
            result.stderr_output.append(buffer, n);
        }
        close(outPipe[0]);
        close(errPipe[0]);

        int status;
        waitpid(pid, &status, 0);
        if (WIFEXITED(status)) {
            result.exit_code = WEXITSTATUS(status);
        } else {
            result.exit_code = -1;
        }
    } else {
        result.stderr_output = "Fork failed";
        return result;
    }

    auto end_time = std::chrono::steady_clock::now();
    result.duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
    return result;
}

#endif

} // namespace sentinel
