#pragma once

#include <string>
#include <vector>
#include "sentinel/model/domain_models.hpp"
#include "sentinel/common/errors.hpp"

namespace sentinel {

class HarnessGenerator {
public:
    static HarnessResult generate(const HarnessRequest& request);

    static std::string generateStubsHeader(const std::vector<StubConfiguration>& stubs, const std::string& targetHeader = "");
    static std::string generateStubsSource(const std::vector<StubConfiguration>& stubs);
    static std::string generateTestVectorsSource(const std::vector<TestVector>& vectors, const FunctionInfo& targetFunction);
    static std::string generateMainHarness(const HarnessRequest& request);
};

} // namespace sentinel
