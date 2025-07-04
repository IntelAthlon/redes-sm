#include <iostream>
#include <vector>
#include <cstring>
#include <ctime>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <random>
#include <thread>
// Includes dependientes de SO
#ifdef _WIN32
// Para Windows usar winsock
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  #define CLOSESOCKET closesocket
  typedef int socklen_t;
#else
// Para Linux/Unix usar sockets POSIX
  #include <arpa/inet.h>
  #include <unistd.h>
  #include <sys/socket.h>
  #include <netinet/in.h>
  #define CLOSESOCKET close
#endif

// OpenSSL para firma

#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/bio.h>


// Struct de los datos sensor
#pragma pack(push, 1)
struct SensorData {
    int16_t id;
    uint64_t fecha_hora; // Timestamp tipo AAAAMMDDHHMMSS
    float temperatura;
    float presion;
    float humedad;
};
#pragma pack(pop)

// generador timestamp
uint64_t defFechaHora() {
    time_t now = time(nullptr);
    struct tm* lt = localtime(&now);
    char buffer[15];
    snprintf(buffer, sizeof(buffer), "%04d%02d%02d%02d%02d%02d",
             lt->tm_year + 1900, lt->tm_mon + 1, lt->tm_mday,
             lt->tm_hour, lt->tm_min, lt->tm_sec);
    return std::stoull(buffer);
}

// Firma RSA (codigo placeholder de IA)
bool signData(const uint8_t* data, size_t len, std::vector<uint8_t>& out_signature, const std::string& priv_key_path) {
    // Leer el archivo como texto (clave PEM)
    std::ifstream file(priv_key_path);
    if (!file.is_open()) return false;

    std::stringstream buffer;
    buffer << file.rdbuf();
    std::string key_str = buffer.str();
    file.close();

    // Crear un BIO en memoria con la clave leída
    BIO* bio = BIO_new_mem_buf(key_str.data(), static_cast<int>(key_str.size()));
    if (!bio) return false;

    // Leer la clave privada desde el BIO
    EVP_PKEY* pkey = PEM_read_bio_PrivateKey(bio, nullptr, nullptr, nullptr);
    BIO_free(bio);
    if (!pkey) return false;

    // Crear contexto para firmar
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) {
        EVP_PKEY_free(pkey);
        return false;
    }

    bool success = false;
    if (EVP_DigestSignInit(ctx, nullptr, EVP_sha256(), nullptr, pkey) == 1 &&
        EVP_DigestSignUpdate(ctx, data, len) == 1) {

        size_t siglen = 0;
        if (EVP_DigestSignFinal(ctx, nullptr, &siglen) == 1) {
            out_signature.resize(siglen);
            if (EVP_DigestSignFinal(ctx, out_signature.data(), &siglen) == 1) {
                out_signature.resize(siglen);  // Redimensionar por si es más corta
                success = true;
            }
        }
        }

    EVP_MD_CTX_free(ctx);
    EVP_PKEY_free(pkey);
    return success;

}
// Simula datos aleatorios para un sensor con un ID dado
SensorData generateRandomSensorData(int16_t id) {
    static std::default_random_engine gen(std::random_device{}()); // motor aleatorio
    static std::uniform_real_distribution<float> temp(20.0f, 30.0f);   // temperatura entre 20 y 30 °C
    static std::uniform_real_distribution<float> pres(990.0f, 1025.0f); // presión entre 990 y 1025 hPa
    static std::uniform_real_distribution<float> hum(30.0f, 70.0f);    // humedad entre 30% y 70%

    SensorData data;
    data.id = id;
    data.fecha_hora = defFechaHora(); // timestamp tipo AAAAMMDDHHMMSS
    data.temperatura = temp(gen);
    data.presion = pres(gen);
    data.humedad = hum(gen);
    return data;
}

bool sendSensorPacket(const SensorData& data, const std::string& host, uint16_t port, const std::string& priv_key_path) {
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {
        std::cerr << "[X] WSAStartup falló.\n";
        return false;
    }
#endif

    // Serializa SensorData
    uint8_t buffer[sizeof(SensorData)];
    memcpy(buffer, &data, sizeof(SensorData));

    // Firma
    std::vector<uint8_t> signature;
    if (!signData(buffer, sizeof(SensorData), signature, priv_key_path)) {
        std::cerr << "[X] Firma fallida.\n";
#ifdef _WIN32
        WSACleanup();
#endif
        return false;
    }

    // Construye paquete: [SensorData][Firma]
    std::vector<uint8_t> packet(sizeof(SensorData) + signature.size());
    memcpy(packet.data(), buffer, sizeof(SensorData));
    memcpy(packet.data() + sizeof(SensorData), signature.data(), signature.size());

    // Socket TCP
    socklen_t sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        std::cerr << "[X] Error al crear socket.\n";
#ifdef _WIN32
        WSACleanup();
#endif
        return false;
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    if (inet_pton(AF_INET, host.c_str(), &serverAddr.sin_addr) <= 0) {
        std::cerr << "[X] Dirección IP inválida.\n";
        CLOSESOCKET(sock);
#ifdef _WIN32
        WSACleanup();
#endif
        return false;
    }

    if (connect(sock, (sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
        std::cerr << "[X] Fallo al conectar a " << host << ":" << port << "\n";
        CLOSESOCKET(sock);
#ifdef _WIN32
        WSACleanup();
#endif
        return false;
    }

    size_t total_sent = 0;
    size_t packet_size = packet.size();
    while (total_sent < packet_size) {
        int sent = send(sock, reinterpret_cast<const char*>(packet.data()) + total_sent, static_cast<int>(packet_size - total_sent), 0);
        if (sent <= 0) {
            std::cerr << "[X] Error al enviar datos.\n";
            CLOSESOCKET(sock);
#ifdef _WIN32
            WSACleanup();
#endif
            return false;
        }
        total_sent += sent;
    }

    std::cout << "[✓] Datos enviados correctamente: ID=" << data.id << ", Temp=" << data.temperatura << "\n";

    CLOSESOCKET(sock);

#ifdef _WIN32
    WSACleanup();
#endif

    return true;
}

// Función principal
int main() {
#ifdef _WIN32
    // Inicializa Winsock en Windows
    WSADATA wsa;
    WSAStartup(MAKEWORD(2,2), &wsa);
#endif

    // Configuración básica del sensor
    const int16_t sensor_id = 101;
    const std::string server_ip = "127.0.0.1"; // dirección del servidor - localhost como prueba
    // despues definimos la forma en la que elige y conecta IP
    const uint16_t server_port = 4000;         // puerto del servidor, debemos determinar uno fijo
    const std::string private_key_path = "private.pem"; // clave privada local

    // Bucle principal: envía datos cada 5 segundos
    while (true) {
        SensorData data = generateRandomSensorData(sensor_id); // genera datos simulados
        sendSensorPacket(data, server_ip, server_port, private_key_path); // los firma y envía
        std::this_thread::sleep_for(std::chrono::seconds(5)); // espera 5 segundos

    }

#ifdef _WIN32
    // Limpieza de Winsock en Windows
    WSACleanup();
#endif
    return 0;
}
