#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h> // Needed to modify transmission power
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#define PIR_PIN        13
#define LDR_PIN        34
#define uS_TO_S_FACTOR 1000000 // Used to make the conversion between seconds and microseconds
#define TIME_TO_SLEEP  4.5  // Deep sleep duration: X = 4.5 seconds

// Boot counter stored in RTC memory (survives deep sleep)
RTC_DATA_ATTR int bootCount = 0;

// Sink node broadcast address
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ESP-NOW peer structure for sink node registration
esp_now_peer_info_t peerInfo;

// [IMPROVEMENT] volatile flag instead of a fixed delay waiting for callback from sink.
volatile bool messageSent = false;

// Print wakeup reason (on real hardware shows TIMER from 2nd boot onwards)
void print_wakeup_reason() {
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("[WAKEUP] Timer"); break;
    default:
      Serial.println("[WAKEUP] Power on or reset"); break;
  }
}

// Sending callback
void OnDataSent(const wifi_tx_info_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("[TX] Send Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Ok" : "Error");
  // [IMPROVEMENT] callback that signals transmission has ended
  messageSent = true;
}

void setup() {
  // Disable brownout detector
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);
  //[IMPROVEMENT] Reduce initial delay from 1 s to 10 ms
  delay(10);

  // Increment boot count on every wake-up
  ++bootCount;
  Serial.println("Boot number: " + String(bootCount));
  print_wakeup_reason();

  // Read sensors and measure time
  unsigned long t_sensor = micros();
  pinMode(PIR_PIN, INPUT);
  bool motion = digitalRead(PIR_PIN);
  analogReadResolution(12); // Set ADC resolution to 12 bit (values 0-4095)
  int lux = analogRead(LDR_PIN);
  Serial.printf("[TIMING] Sensor read: %lu us\n", micros() - t_sensor);

  // Build message in the required challenge format
  String msg = motion
    ? "MOTION_DETECTED-LUMINOSITY:"     + String(lux)
    : "MOTION_NOT_DETECTED-LUMINOSITY:" + String(lux);
  Serial.println("[MSG] " + msg);

  // Initialize WiFi and ESP-NOW and measure time this is the longest active phase (~200ms)
  unsigned long t_wifi = micros();
  WiFi.mode(WIFI_STA);
  esp_now_init();
  // [IMPROVEMENT]: Reduce tx power from 19.5 dBm to 2 dBm
  esp_wifi_set_max_tx_power(8);
  esp_now_register_send_cb(OnDataSent); // Register send callback

  // Register sink node as peer using broadcast address
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);
  Serial.printf("[TIMING] WiFi+ESP-NOW init: %lu us\n", micros() - t_wifi);

  // Transmit message and measure time
  unsigned long t_tx = micros();
  // Cast String to uint8_t array, +1 to include null terminator
  esp_now_send(broadcastAddress, (uint8_t*)msg.c_str(), msg.length() + 1);
  // [IMPROVEMENT] waits for callback from sink and immediately exits (decreases t_tx)
  unsigned long t_wait = millis(); // timeout to avoid infinite loops
  while (!messageSent && millis() - t_wait < 50) { 
      delay(1); 
  }
  Serial.printf("[TIMING] TX: %lu us\n", micros() - t_tx);

  // Enter deep sleep for X seconds
  Serial.println("Going to sleep now");
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.flush(); // Flush serial buffer before sleeping
  esp_deep_sleep_start(); // Enter deep sleep
}

void loop() {
  // Never reached - deep sleep causes a full reset on wake-up
}