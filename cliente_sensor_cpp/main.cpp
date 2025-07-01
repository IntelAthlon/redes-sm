#include <iostream>
#include <cstring>
#include <ctime>
#include <cstdint>

struct SensorData {
    int16_t id;
    uint64_t timestamp;
    float temperatura;
    float presion;
    float humedad;
};

int main()
{
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
