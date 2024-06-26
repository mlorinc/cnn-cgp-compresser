#include "StringTemplate.h"
#include <regex>
#include <sstream>
#include <ostream>

using namespace cgp;

std::string cgp::replace_string_variables(const std::string& input, const std::unordered_map<std::string, std::string>& variables) {
    std::string result = "";
    std::string text = input;
    std::regex placeholder_regex(R"(\{(\w+)\})");
    std::smatch match;

    while (std::regex_search(text, match, placeholder_regex)) {
        auto it = variables.find(match[1].str());
        result += match.prefix();
        if (it != variables.end()) {
            result += it->second;
        }
        text = match.suffix().str();
    }
    result += text;
    return result;
}

cgp::StringTemplateError::StringTemplateError(const std::vector<std::string>& missing_arguments) : std::invalid_argument("missing variable definitions")
{
    if (missing_arguments.empty())
    {
        throw std::runtime_error("StringTemplateError cannot be created with empty vector");
    }

    std::ostringstream builder;
    auto it = missing_arguments.cbegin(), real_end = missing_arguments.cend(), end = real_end - 1;
    builder << "missing variables: ";

    while (it != end)
    {
        builder << *it++ << ", ";
    }
    
    if (it != real_end)
    {
        builder << *it;
    }
    message = builder.str();
}

std::string StringTemplateError::get_message() const
{
    return message;
}
