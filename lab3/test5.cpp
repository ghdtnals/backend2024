#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>
#include <iostream>
#include <string>

using namespace std;

int main() {
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0) return 1;

    struct sockaddr_in sin;
   
    memset(&sin, 0, sizeof(sin)); //모든 멤버 0으로 초기화
    sin.sin_family = AF_INET;
    sin.sin_port = htons(10133);
    sin.sin_addr.s_addr = inet_addr("127.0.0.1"); //inet_addr:"127.0.0.1" 4바이트로 변환 (network byte order: big endian)
    
    string buf;
    char buf2[65536];

    while(getline(cin,buf)){
        int numBytes = sendto(s, buf.c_str(), buf.length(),
        0, (struct sockaddr *) &sin, sizeof(sin));
        cout << "Sent: " << numBytes << endl;
    
        memset(&sin, 0, sizeof(sin));
        memset(buf2, 0, sizeof(buf2)); 

        socklen_t sin_size = sizeof(sin);
        numBytes = recvfrom(s, buf2, sizeof(buf2), 0, (struct sockaddr *) &sin, &sin_size);
        cout << "Recevied: " << numBytes << endl;
        cout << "From " << inet_ntoa(sin.sin_addr) << endl;

         if (numBytes > 0) {
            cout<< buf2 << endl;
        } else {
            cout << "Error receiving data" << endl;
        }
    }
    
    close(s);
    
   return 0;
}