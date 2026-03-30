import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# COMPUTE PARAMETERS
# ==========================================
leader_code = 10889590
AB = leader_code % 100
ABCD = leader_code % 10000

X_sleep = (AB % 50 + 5) / 10
Y_battery = ABCD % 5000 + 15000

print("-" * 40)
print("PARAMETERS")
print(f"Deep sleep duration: {X_sleep} [s]")
print(f"Battery energy level: {Y_battery} [J]")
print("-" * 40)

# ==========================================
# VISUALIZE CSV DATA
# ==========================================
def plot_power(filename, label):
    df = pd.read_csv(filename)

    plt.plot(df['Timestamp'], df['Data'], label=label)
    plt.xlabel('Time (s)')
    plt.ylabel('Power (mW)')
    plt.title(f'Power Consumption: {label}')
    plt.show()

#plot_power(filename='data/deep_sleep.csv', label='Deep Sleep')
#plot_power(filename='data/sender.csv', label='Sender')
#plot_power(filename='data/sensor-read.csv', label='Sensor Read')

# ==========================================
# TIME DATA FROM WOKWI
# ==========================================
t_boot = 1 # 1 s
t_sense = 0.00043  # 430 us
t_init = 0.19600  # 196 ms (WiFi + ESP-NOW init)
t_tx = 0.09930  # 99.3 ms (TX + delay)
t_sleep = X_sleep  # 4.5 s

# ==========================================
# COMPUTE AVG POWER FROM CSV
# ==========================================
# fallback values
p_boot = 300.0
p_sleep = 50.0
p_init = 635.0
p_tx = 690.0
p_sense = 250.0

try:
    # Extract from deep_sleep.csv
    df_ds = pd.read_csv('esp32-motion-sensor-best/data/deep_sleep.csv')
    power_ds = df_ds.iloc[:, 1]
    p_sleep = power_ds[power_ds < 100].mean()
    p_init = power_ds[power_ds > 500].mean()
    p_boot = power_ds[power_ds.between(200, 300)].mean()

    # Extract from sender.csv (Peak at 19.5 dBm)
    df_tx = pd.read_csv('data/sender.csv')
    power_tx = df_tx.iloc[:, 1]
    p_tx = power_tx[power_tx > 680].max()

    # Extract from sensor_read.csv
    df_sr = pd.read_csv('data/sensor-read.csv')
    power_sr = df_sr.iloc[:, 1]
    p_sense = power_sr[(power_sr > 200) & (power_sr < 300)].mean()

    print("Data successfully loaded from CSV.")
except Exception as e:
    print(f"Error in reading CSV ({e}). Using fallback values.")

print(f"\nMean Power Estimated (mW):")
print(f" - Boot: {p_boot:.2f} mW")
print(f" - Sensing: {p_sense:.2f} mW")
print(f" - WiFi Init: {p_init:.2f} mW")
print(f" - TX (19.5 dBm): {p_tx:.2f} mW")
print(f" - Deep Sleep: {p_sleep:.2f} mW")

# ==========================================
# COMPUTE ENERGY CONSUMPTION
# ==========================================
# E = P(W) * t(s)
E_boot = (p_boot / 1000) * t_boot
E_sense = (p_sense / 1000) * t_sense
E_init = (p_init / 1000) * t_init
E_tx = (p_tx / 1000) * t_tx
E_sleep = (p_sleep / 1000) * t_sleep

E_cycle = E_boot + E_sense + E_init + E_tx + E_sleep
T_cycle = t_boot + t_sense + t_init + t_tx + t_sleep

tot_cycles = Y_battery / E_cycle
lifetime_sec = tot_cycles * T_cycle
lifetime_days = lifetime_sec / 86400

print("-" * 40)
print(f"ENERGY PER CYCLE: {E_cycle:.5f} Joules")
print(f"ESTIMATED LIFETIME: {lifetime_days:.2f} Days")
print("-" * 40)

# ==========================================
# GENERATE POWER-VS-TIME GRAPH
# ==========================================
# Costruisco l'asse dei tempi cumulativo
times = [
    0,
    t_boot, t_boot,
    t_boot + t_sense, t_boot + t_sense,
    t_boot + t_sense + t_init, t_boot + t_sense + t_init,
    t_boot + t_sense + t_init + t_tx, t_boot + t_sense + t_init + t_tx,
    t_boot + t_sense + t_init + t_tx + t_sleep
]

# Associo i livelli di potenza corrispondenti
powers = [
    p_boot, p_boot,
    p_sense, p_sense,
    p_init, p_init,
    p_tx, p_tx,
    p_sleep, p_sleep
]

plt.figure(figsize=(12, 6))

# Disegno il grafico a gradini
plt.step(times, powers, where='post', color='darkblue', linewidth=2.5, label='Original Profiling (19.5 dBm)')
plt.fill_between(times, powers, step="post", alpha=0.15, color='royalblue')

# Etichette delle Fasi
plt.text(t_boot /2, p_boot + 20, 'Boot', ha='center', fontsize=9, fontweight='bold')
plt.text(t_boot + t_sense / 2, p_sense + 20, 'Sensing', ha='center', fontsize=9, fontweight='bold')
plt.text(t_boot + t_sense + t_init / 2, p_init + 20, 'WiFi Init', ha='center', fontsize=9, fontweight='bold')
plt.text(t_boot + t_sense + t_init + t_tx / 2, p_tx + 20, 'TX', ha='center', fontsize=9, fontweight='bold')
plt.text(t_boot + t_sense + t_init + t_tx + t_sleep / 2, p_sleep + 20, f'Deep Sleep\n({X_sleep}s)', ha='center', fontsize=10,
         fontweight='bold')

# Formattazione del grafico
plt.xlabel('Time (s)', fontsize=12)
plt.ylabel('Power Consumption (mW)', fontsize=12)
plt.title(f'IoT Motion Sensor: Power Profile for One Complete Cycle\nEstimated Lifetime: {lifetime_days:.1f} Days',
          fontsize=14)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.ylim(0, max(powers) + 100)
plt.legend(loc='upper right')
plt.tight_layout()

# Salva l'immagine per il report (opzionale) e la mostra a schermo
# plt.savefig('power_profile_cycle.png', dpi=300)
plt.show()