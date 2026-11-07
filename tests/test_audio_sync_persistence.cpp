#include "mod_packages.h"
#include <chrono>
#include <filesystem>
#include <iostream>
#include <stdexcept>

using namespace PSXRecompV4;
namespace fs = std::filesystem;
static void check(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}
int main(int argc, char** argv) {
    check(argc == 2, "Pass the Audio Sync manifest path");
    const auto nonce = std::chrono::steady_clock::now().time_since_epoch().count();
    const fs::path root = fs::temp_directory_path() /
        ("tomba-audio-persistence-" + std::to_string(nonce));
    const fs::path package = root / "packages/psx.audio.low-latency/1.0.1";
    fs::create_directories(package);
    fs::copy_file(argv[1], package / "manifest.toml");
    const char* id = "psx.audio.low-latency";
    const char* feature = "low-latency-audio";
    const char* option = "target_ms";
    std::string error;
    ModPackageManager fresh(root);
    check(fresh.scan(&error) && fresh.load_state(&error), error);
    check(fresh.feature_option_value(id, feature, option) == "70", "fresh 70");
    check(fresh.set_feature_option(id, feature, option, "80", &error) &&
          fresh.save_state(&error), error);
    ModPackageManager saved(root);
    check(saved.scan(&error) && saved.load_state(&error), error);
    check(saved.feature_option_value(id, feature, option) == "80", "saved 80 retained");
    check(saved.set_feature_option(id, feature, option, "180", &error), "upper bound");
    check(saved.set_feature_option(id, feature, option, "70", &error) &&
          saved.save_state(&error), error);
    ModPackageManager reset(root);
    check(reset.scan(&error) && reset.load_state(&error), error);
    check(reset.feature_option_value(id, feature, option) == "70", "reset 70 retained");
    fs::remove_all(root);
    std::cout << "PASS fresh70, saved80, upper180 and reset70 persistence\n";
}
