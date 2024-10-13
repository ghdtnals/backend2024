#include <fstream>
#include <string>
#include <iostream>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#include "person.pb.h"

using namespace std;
using namespace mju;

int main() {
    // Person 객체 생성 및 초기화
    Person *p = new Person;
    p->set_name("MJ Kim");
    p->set_id(12345678);

    Person::PhoneNumber* phone = p->add_phones();
    phone->set_number("010-111-1234");
    phone->set_type(Person::MOBILE);

    phone = p->add_phones();
    phone->set_number("02-100-1000");
    phone->set_type(Person::HOME);

    // 직렬화
    const string s = p->SerializeAsString();
    cout << "Length: " << s.length() << endl;

    // UDP 소켓 생성
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        cerr << "Socket creation failed" << endl;
        return 1;
    }

    // 서버 주소 설정
    struct sockaddr_in serverAddr;
    memset(&serverAddr, 0, sizeof(serverAddr));
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(10001); // 서버 포트
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1"); // 서버 IP

    // 데이터 전송
    int numBytes = sendto(sock, s.c_str(), s.length(), 0, (struct sockaddr *)&serverAddr, sizeof(serverAddr));
    cout << "Sent: " << numBytes << " bytes" << endl;

    // 데이터 수신
    char buf[65536];
    memset(buf, 0, sizeof(buf));
    socklen_t addrLen = sizeof(serverAddr);
    numBytes = recvfrom(sock, buf, sizeof(buf), 0, (struct sockaddr *)&serverAddr, &addrLen);
    if (numBytes < 0) {
        perror("recvfrom error");
    } else {
        cout << "Received: " << numBytes << " bytes" << endl;

        // 수신된 데이터를 역직렬화
        Person *p2 = new Person;
        if (p2->ParseFromString(string(buf, numBytes))) {
            cout << "Name: " << p2->name() << endl;
            cout << "ID: " << p2->id() << endl;
            for (int i = 0; i < p2->phones_size(); ++i) {
                cout << "Type: " << p2->phones(i).type() << endl;
                cout << "Phone: " << p2->phones(i).number() << endl;
            }
        } else {
            cerr << "Failed to parse received data" << endl;
        }
            delete p2;
    }

    // 소켓 종료
    close(sock);
    delete p;


    return 0;
}
