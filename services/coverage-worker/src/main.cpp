#include "sentinel/coverage/gcov_provider.hpp"
#include <iostream>
#include <fstream>

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: sentinel-coverage-worker [--gcov <file.gcov>] [--source <file.c> --artifacts <dir>]\n";
        return 1;
    }

    try {
        sentinel::GcovCoverageProvider provider;
        sentinel::CoverageResult result;

        std::string gcovFile;
        std::string sourceFile;
        std::string artifactsDir = ".";

        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--gcov" && i + 1 < argc) {
                gcovFile = argv[++i];
            } else if (arg == "--source" && i + 1 < argc) {
                sourceFile = argv[++i];
            } else if (arg == "--artifacts" && i + 1 < argc) {
                artifactsDir = argv[++i];
            }
        }

        if (!gcovFile.empty()) {
            result = provider.parseGcovFile(gcovFile);
        } else if (!sourceFile.empty()) {
            result = provider.parseCoverage(sourceFile, artifactsDir);
        } else {
            std::cerr << "Error: Either --gcov or --source must be specified.\n";
            return 1;
        }

        std::cout << result.toJson().dump(2) << "\n";
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Coverage Worker Error: " << e.what() << "\n";
        return 2;
    }
}
