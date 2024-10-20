#include <chrono>
#include <iostream>
#include <thread>

using namespace std;

int sum = 0;

void f() {
 for (int i = 0; i < 1000; ++i) {
 ++sum;
 }
} 
//sum 변수에 대한 접근이 스레드간에 동기화되지 않기 때문에 
//여러 스레드가 sum에 접근할 경우 데이터 손실이 발생할 수 있다. 
int main() {
 thread t(f);
 for (int i = 0; i < 1000; ++i) {
  ++sum;
}
 t.join();
 cout << "Sum: " << sum << endl;
}

