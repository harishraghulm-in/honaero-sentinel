#include "sentinel/coverage/gcov_provider.hpp"
#include "sentinel/common/process.hpp"
#include <fstream>
#include <sstream>
#include <filesystem>
#include <iostream>

namespace sentinel {

namespace fs = std::filesystem;

GcovCoverageProvider::GcovCoverageProvider(std::string gcov_binary)
    : gcov_binary_(std::move(gcov_binary)) {}

CoverageResult GcovCoverageProvider::parseCoverage(
    const std::string& source_file,
    const std::string& artifacts_directory)
{
    fs::path artDir(artifacts_directory);
    fs::path srcPath(source_file);
    std::string baseFilename = srcPath.filename().string();

    // Check if .gcov file already exists, or if we need to invoke gcov
    fs::path directGcov = artDir / (baseFilename + ".gcov");
    if (!fs::exists(directGcov)) {
        // Look for .gcda and .gcno files
        fs::path gcda = artDir / (srcPath.stem().string() + ".gcda");
        fs::path gcno = artDir / (srcPath.stem().string() + ".gcno");

        if (!fs::exists(gcda) || !fs::exists(gcno)) {
            throw CoverageError(
                "GCOV coverage artifacts missing (.gcda/.gcno)",
                "Expected artifacts in directory: " + artifacts_directory + " for source: " + baseFilename,
                SourceLocation{source_file, 0, 0}
            );
        }

        // Run gcov command
        auto proc = ProcessRunner::execute(
            gcov_binary_,
            {"-b", "-c", baseFilename},
            artifacts_directory
        );

        if (proc.exit_code != 0 || !fs::exists(directGcov)) {
            throw CoverageError(
                "gcov execution failed or failed to generate .gcov",
                proc.stderr_output.empty() ? proc.stdout_output : proc.stderr_output,
                SourceLocation{source_file, 0, 0}
            );
        }
    }

    return parseGcovFile(directGcov.string());
}

CoverageResult GcovCoverageProvider::parseGcovFile(const std::string& gcov_file_path) {
    std::ifstream file(gcov_file_path);
    if (!file.is_open()) {
        throw CoverageError("Failed to open .gcov file for reading", gcov_file_path);
    }

    CoverageResult result;
    result.source_file = gcov_file_path;
    
    std::stringstream rawStream;
    std::string line;
    int currentLineNumber = 0;

    int totalExecutableLines = 0;
    int coveredExecutableLines = 0;
    int totalBranches = 0;
    int coveredBranches = 0;

    while (std::getline(file, line)) {
        rawStream << line << "\n";
        
        // Check for branch records
        if (line.rfind("branch", 0) == 0) {
            // e.g. "branch  0 taken 4 (fallthrough)" or "branch  1 taken 0" or "branch  2 never executed"
            totalBranches++;
            BranchCoverageDetail bDetail;
            bDetail.line = currentLineNumber;
            bDetail.branch_number = totalBranches;

            if (line.find("taken 0") != std::string::npos || line.find("never executed") != std::string::npos) {
                bDetail.taken_count = 0;
                bDetail.covered = false;
            } else {
                bDetail.covered = true;
                coveredBranches++;
                // Try parse taken count
                size_t pos = line.find("taken ");
                if (pos != std::string::npos) {
                    try {
                        bDetail.taken_count = std::stoi(line.substr(pos + 6));
                    } catch (...) {
                        bDetail.taken_count = 1;
                    }
                }
            }
            result.branch_details.push_back(bDetail);
            continue;
        }

        // Standard gcov line format:
        // "<count>:  <line_number>:<source_text>"
        size_t firstColon = line.find(':');
        if (firstColon == std::string::npos) continue;
        size_t secondColon = line.find(':', firstColon + 1);
        if (secondColon == std::string::npos) continue;

        std::string countStr = line.substr(0, firstColon);
        std::string lineNumStr = line.substr(firstColon + 1, secondColon - firstColon - 1);
        std::string sourceText = line.substr(secondColon + 1);

        // Trim whitespace
        countStr.erase(0, countStr.find_first_not_of(" \t"));
        countStr.erase(countStr.find_last_not_of(" \t") + 1);
        lineNumStr.erase(0, lineNumStr.find_first_not_of(" \t"));
        lineNumStr.erase(lineNumStr.find_last_not_of(" \t") + 1);

        int lineNum = 0;
        try {
            lineNum = std::stoi(lineNumStr);
        } catch (...) {
            continue;
        }

        if (lineNum <= 0) continue; // metadata header
        currentLineNumber = lineNum;

        LineCoverageDetail lDetail;
        lDetail.line = lineNum;
        lDetail.source_text = sourceText;

        if (countStr == "-") {
            // Non-executable line
            continue;
        } else if (countStr == "#####") {
            // Uncovered executable line
            totalExecutableLines++;
            lDetail.execution_count = 0;
            lDetail.covered = false;
            result.uncovered_lines.push_back(lineNum);
        } else {
            // Executed line
            totalExecutableLines++;
            coveredExecutableLines++;
            lDetail.covered = true;
            try {
                lDetail.execution_count = std::stoi(countStr);
            } catch (...) {
                lDetail.execution_count = 1;
            }
        }
        result.line_details.push_back(lDetail);
    }

    result.total_lines = totalExecutableLines;
    result.covered_lines = coveredExecutableLines;
    result.statement_coverage_pct = (totalExecutableLines > 0) ? (static_cast<double>(coveredExecutableLines) / totalExecutableLines * 100.0) : 100.0;
    result.line_coverage_pct = result.statement_coverage_pct;

    result.total_branches = totalBranches;
    result.covered_branches = coveredBranches;
    result.branch_coverage_pct = (totalBranches > 0) ? (static_cast<double>(coveredBranches) / totalBranches * 100.0) : 100.0;
    result.function_coverage_pct = (coveredExecutableLines > 0) ? 100.0 : 0.0;
    result.raw_artifact = rawStream.str();

    return result;
}

} // namespace sentinel
