package pl.gps.pozycja;

/**
 * Decyzje o końcu jazdy. Początek i koniec jazdy zgłasza rozpoznawanie aktywności Google
 * („w pojeździe” / „poza pojazdem”); ta klasa potwierdza zgłoszony koniec i obsługuje
 * sytuacje, w których zgłoszenia nie ma. Bez zależności od Androida (zwykły JUnit).
 */
final class DrivePolicy {

    enum Decision { CONTINUE, END_AND_SAVE, END_WITHOUT_SAVE }

    /** Google nadal widzi pojazd, ale bez jazdy tak długo: kończymy, żeby nie trzymać GPS w nieskończoność. */
    static final long CONNECTED_IDLE_LIMIT_MS = 60 * 60_000L;
    /** Poza pojazdem według Google, ale usługa wciąż działa: tyle postoju oznacza parkowanie. */
    static final long DISCONNECTED_STOP_MS = 5 * 60_000L;
    /** Poza pojazdem i bez jazdy od startu: fałszywy alarm. */
    static final long NO_DRIVING_LIMIT_MS = 20 * 60_000L;

    private DrivePolicy() { }

    /**
     * @param inVehicle     czy według rozpoznawania aktywności jesteś teraz w pojeździe
     * @param lastDrivingMs czas ostatniego pomiaru z prędkością jazdy albo -1, jeśli jazdy nie było
     */
    static Decision onWatchdog(boolean inVehicle, long nowMs, long startedAtMs, long lastDrivingMs) {
        boolean drove = lastDrivingMs >= 0;
        long idle = nowMs - (drove ? lastDrivingMs : startedAtMs);

        if (inVehicle) {
            // W pojeździe (korek, czekanie): koniec zgłosi rozpoznawanie aktywności.
            if (idle <= CONNECTED_IDLE_LIMIT_MS) return Decision.CONTINUE;
            return drove ? Decision.END_AND_SAVE : Decision.END_WITHOUT_SAVE;
        }
        if (!drove) {
            return idle > NO_DRIVING_LIMIT_MS ? Decision.END_WITHOUT_SAVE : Decision.CONTINUE;
        }
        // Zgłoszony koniec jazdy został odrzucony (auto ruszyło), a nowe zgłoszenie nie przyszło.
        return idle > DISCONNECTED_STOP_MS ? Decision.END_AND_SAVE : Decision.CONTINUE;
    }

    /** Powiadomienie „Android zablokował śledzenie” pokazujemy najwyżej raz na tyle. */
    static final long BLOCKED_ALERT_INTERVAL_MS = 24 * 60 * 60_000L;

    /** @param lastAlertWallMs czas ostatniego powiadomienia (zegar ścienny) albo 0, jeśli go nie było */
    static boolean shouldAlertBlocked(long lastAlertWallMs, long nowWallMs) {
        return lastAlertWallMs <= 0 || nowWallMs - lastAlertWallMs >= BLOCKED_ALERT_INTERVAL_MS;
    }

    enum ExitDecision { WAIT, RESUMED, CONFIRMED }

    /**
     * Ile czekamy po zgłoszeniu „koniec jazdy”, zanim zapiszemy parking. Google potrafi zgłosić
     * koniec jazdy w długim korku; jeśli w tym czasie auto znów pojedzie, jazda trwa dalej.
     * Opóźnienie nie psuje dokładności: zapisujemy miejsce pierwszego postoju, a nie bieżące.
     */
    static final long EXIT_CONFIRM_MS = 3 * 60_000L;

    /**
     * @param exitEventMs   kiedy według Google skończyła się jazda (czas zdarzenia, nie odbioru)
     * @param lastDrivingMs ostatni pomiar z prędkością jazdy albo -1
     */
    static ExitDecision onExitGrace(long exitEventMs, long nowMs, long lastDrivingMs) {
        if (lastDrivingMs > exitEventMs) return ExitDecision.RESUMED;
        return nowMs - exitEventMs >= EXIT_CONFIRM_MS ? ExitDecision.CONFIRMED : ExitDecision.WAIT;
    }
}
