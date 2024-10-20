#include <chrono>
#include <iostream>
#include <thread>
#include<mutex>

using namespace std;

int sum = 0;
mutex m1;
mutex m2;

void f() {
 for (int i = 0; i < 10*1000*1000; ++i) {
    m1.lock();
    m2.lock();
    ++sum;
    m2.unlock();
    m1.unlock();
 }
} 
//sum 변수에 대한 접근이 스레드간에 동기화되지 않기 때문에 
//여러 스레드가 sum에 접근할 경우 데이터 손실이 발생할 수 있다. 
int main() {
 thread t(f);
 for (int i = 0; i < 10*1000*1000; ++i) {
 m1.lock();
 m2.lock();
 ++sum;
 m2.unlock();
 m1.unlock();
}
 t.join();
 cout << "Sum: " << sum << endl;
}