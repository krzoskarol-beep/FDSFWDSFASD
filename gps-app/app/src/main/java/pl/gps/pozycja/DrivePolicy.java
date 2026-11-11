package pl.gps.pozycja;

/**
 * Co minutę usługa jazdy pyta, czy jazda nadal trwa. Zwykle koniec jazdy zgłasza rozłączenie
 * z Bluetooth auta; ta klasa obsługuje sytuacje, w których takiego zgłoszenia nie ma.
 * Bez zależności od Androida, więc testowana zwykłym JUnitem.
 */
final class DrivePolicy {

    enum Decision { CONTINUE, END_AND_SAVE, END_WITHOUT_SAVE }

    /** Połączony z autem, ale bez jazdy tak długo: radio zostało włączone po zgaszeniu silnika. */
    static final long CONNECTED_IDLE_LIMIT_MS = 60 * 60_000L;
    /** Po zignorowanym zerwaniu Bluetooth: tyle postoju oznacza parkowanie. */
    static final long DISCONNECTED_STOP_MS = 5 * 60_000L;
    /** Bez połączenia z autem i bez jazdy od startu: fałszywy alarm. */
    static final long NO_DRIVING_LIMIT_MS = 20 * 60_000L;

    private DrivePolicy() { }

    /**
     * @param carConnected  czy telefon jest teraz połączony z Bluetooth auta
     * @param lastDrivingMs czas ostatniego pomiaru z prędkością jazdy albo -1, jeśli jazdy nie było
     */
    static Decision onWatchdog(boolean carConnected, long nowMs, long startedAtMs, long lastDrivingMs) {
        boolean drove = lastDrivingMs >= 0;
        long idle = nowMs - (drove ? lastDrivingMs : startedAtMs);

        if (carConnected) {
            // W aucie (korek, czekanie z włączonym silnikiem): koniec zgłosi rozłączenie.
            if (idle <= CONNECTED_IDLE_LIMIT_MS) return Decision.CONTINUE;
            return drove ? Decision.END_AND_SAVE : Decision.END_WITHOUT_SAVE;
        }
        if (!drove) {
            return idle > NO_DRIVING_LIMIT_MS ? Decision.END_WITHOUT_SAVE : Decision.CONTINUE;
        }
        // Rozłączenie w trasie zostało zignorowane, a ponowne połączenie nie przyszło.
        return idle > DISCONNECTED_STOP_MS ? Decision.END_AND_SAVE : Decision.CONTINUE;
    }

    /** Powiadomienie „Android zablokował śledzenie” pokazujemy najwyżej raz na tyle. */
    static final long BLOCKED_ALERT_INTERVAL_MS = 24 * 60 * 60_000L;

    /** @param lastAlertWallMs czas ostatniego powiadomienia (zegar ścienny) albo 0, jeśli go nie było */
    static boolean shouldAlertBlocked(long lastAlertWallMs, long nowWallMs) {
        return lastAlertWallMs <= 0 || nowWallMs - lastAlertWallMs >= BLOCKED_ALERT_INTERVAL_MS;
    }
}
