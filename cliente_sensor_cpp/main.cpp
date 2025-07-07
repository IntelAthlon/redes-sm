#include <iostream>
#include <vector>
#include <cstring>
#include <ctime>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <random>
#include <thread>
#include <iomanip>
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
// namespace estandar
using namespace std;

// Struct de los datos sensor
#pragma pack(push, 1) // Usamos pragma para indicarle al compilador que no queremos padding
// Alineación de 1 byte para evitar padding entre campos
struct SensorData {
    int16_t id;
    uint64_t fecha_hora; // Timestamp tipo AAAAMMDDHHMMSS
    float temperatura;
    float presion;
    float humedad;
};
#pragma pack(pop) // Volvemos a la alineación por defecto

// generador timestamp
uint64_t defFechaHora() {
    time_t hora = time(nullptr);
    tm* horalocal = std::localtime(&hora);

    // Crear un stringstream para formatear la fecha y hora
    std::ostringstream timestamp;
    timestamp << put_time(horalocal, "%Y%m%d%H%M%S");
    return stoull(timestamp.str());
}

// Simula datos aleatorios para un sensor con un ID dado
SensorData datosRandom(int16_t id) {
    static default_random_engine gen(random_device{}()); // motor aleatorio
    static uniform_real_distribution<float> temp(20.0f, 30.0f);   // temperatura entre 20 y 30 °C
    static uniform_real_distribution<float> pres(990.0f, 1025.0f); // presión entre 990 y 1025 hPa
    static uniform_real_distribution<float> hum(30.0f, 70.0f);    // humedad entre 30% y 70%

    SensorData datos;
    datos.id = id;
    datos.fecha_hora = defFechaHora();
    datos.temperatura = temp(gen);
    datos.presion = pres(gen);
    datos.humedad = hum(gen);
    return datos;
}

// Firma RSA
bool firmar(const uint8_t* datos, size_t tam, vector<uint8_t>& salida){
    // leer clave privada como texto
    ifstream file("private.pem"); // Ruta fija, debe estar junto al ejecutable
    if(!file.is_open()) return false;

    stringstream buffer;
    buffer << file.rdbuf();
    string token = buffer.str();
    file.close();

    // crear un BIO en memoria con la clave leída
    BIO* bio = BIO_new_mem_buf(token.data(),(int)(token.size()));
    if(!bio) return false;

    // leer la clave privada desde el BIO
    EVP_PKEY* pkey = PEM_read_bio_PrivateKey(bio, nullptr, nullptr, nullptr);
    BIO_free(bio);
    if(!pkey) return false;

    // crear contexto para firmar
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) {
        EVP_PKEY_free(pkey);
        return false;
    }

     // Inicializar el contexto de firma con SHA256
    if (EVP_DigestSignInit(ctx,nullptr,EVP_sha256(),nullptr,pkey)==1 && EVP_DigestSignUpdate(ctx,datos,tam)==1) {
        size_t tamanoFirma = 0;
        if (EVP_DigestSignFinal(ctx,nullptr,&tamanoFirma) == 1) {
            salida.resize(tamanoFirma);
            if (EVP_DigestSignFinal(ctx,salida.data(),&tamanoFirma) == 1) {
                salida.resize(tamanoFirma);  // Redimensionar por si es más corta
                EVP_MD_CTX_free(ctx);
                EVP_PKEY_free(pkey);
                return true;
            }
        }
    }

    EVP_MD_CTX_free(ctx);
    EVP_PKEY_free(pkey);
    return false;

}

bool enviarPaquete(SensorData& datos, string &ip, int puerto) {
    // Serializa SensorData
    uint8_t buffer[sizeof(SensorData)];
    memcpy(buffer,&datos,sizeof(SensorData));

    // generar firma de paquete
    vector<uint8_t> firma;
    if (!firmar(buffer,sizeof(SensorData),firma)) {
        cerr<<"Error: No se pudo firmar"<<endl;
        #ifdef _WIN32
        WSACleanup();
        #endif
        return false;
    }

    // construye paquete con firma incluida
    vector<uint8_t> paquete(sizeof(SensorData)+firma.size());
    memcpy(paquete.data(), buffer, sizeof(SensorData));
    memcpy(paquete.data() + sizeof(SensorData), firma.data(), firma.size());

    // Socket TCP
    socklen_t sock = socket(AF_INET,SOCK_STREAM,0);
    if (sock < 0) {
        cerr<<"Error: No se pudo crear el socket"<<endl;
        #ifdef _WIN32
        WSACleanup();
        #endif
        return false;
    }

    sockaddr_in direccionServidor{};
    direccionServidor.sin_family = AF_INET;
    direccionServidor.sin_port = htons(puerto);
    if (inet_pton(AF_INET, ip.c_str(), &direccionServidor.sin_addr) <= 0) {
        cerr<<"ip invalida"<<endl;
        CLOSESOCKET(sock);
        #ifdef _WIN32
        WSACleanup();
        #endif
        return false;
    }

    if (connect(sock,(sockaddr*)&direccionServidor, sizeof(direccionServidor)) < 0) {
        cerr<<"no se pudo conectar a"<<ip<<":"<<puerto<<endl;
        CLOSESOCKET(sock);
        #ifdef _WIN32
        WSACleanup();
        #endif
        return false;
    }

    size_t total = 0;
    size_t tamanoPaquete = paquete.size();
    while (total < tamanoPaquete) {
        int tamanoEnviado = send(sock,reinterpret_cast<const char*>(paquete.data())+total, (int)(tamanoPaquete - total),0);
        if (tamanoEnviado <= 0) {
            cerr<<"tamaño de paquete invalido o error al enviar"<<endl;
            CLOSESOCKET(sock);
            #ifdef _WIN32
            WSACleanup();
            #endif
            return false;
        }
        total += tamanoEnviado;
    }

    cout<<"Datos enviados correctamente: ID="<<datos.id<<", Temp="<<datos.temperatura<<", Presion="<<datos.presion<<", Humedad="<<datos.humedad<<endl;
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

    // leer configuración desde archivo externo, ruta fija, junto al ejecutable
    int16_t sensor_id;
    string ip;
    int puerto;
    ifstream config("config.txt");
    if (!config.is_open()) {
        cerr << "Error al leer la configuración"<<endl;
        #ifdef _WIN32
        WSACleanup();
        #endif
        return 1;
    }

    string token;
    while (getline(config,token)) {
        istringstream ss(token);
        string key,value;
        if(getline(ss,key,'=') && getline(ss,value)){
            if(key=="sensor_id"){
                sensor_id = (int16_t)stoi(value);
            }else if(key=="server_ip"){
                ip=value;
            }else if(key=="server_port"){
                puerto=stoi(value);
            }
        }
    }
    config.close();

    // while principal envía datos cada 5 segundos
    while (true) {
        SensorData data = datosRandom(sensor_id); // genera datos simulados
        enviarPaquete(data,ip,puerto); // los firma y envía
        this_thread::sleep_for(chrono::seconds(5)); // espera 5 segundos
    }
}
