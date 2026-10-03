#include "signed_firmware.h"
#include "board_profile.h"
#include <cassert>
#include <cstring>
#include <iostream>
int main() {
    const signed_firmware::BoardFirmwareIdentity identity={
        signed_firmware::makeIdentity("0.8.0"),TRESVIZO_HARDWARE_ID};
    const auto* bytes=reinterpret_cast<const uint8_t*>(&identity);
    assert(signed_firmware::requiresSignature(bytes,sizeof(identity)));
    const auto* board=bytes+32;
    assert(signed_firmware::matchesHardware(board,48,board_profile::kHardwareId));
    assert(!signed_firmware::matchesHardware(board,47,board_profile::kHardwareId));
    assert(!signed_firmware::matchesHardware(board,48,"tresvizo-esp32s3-4m-v1"));
    uint8_t malformed[48];std::memset(malformed,'x',sizeof(malformed));
    assert(!signed_firmware::matchesHardware(malformed,sizeof(malformed),board_profile::kHardwareId));
    assert(!signed_firmware::matchesHardware(nullptr,48,board_profile::kHardwareId));
    std::cout<<"board_identity: rechaza otra placa e identidades truncadas OK\n";
}
