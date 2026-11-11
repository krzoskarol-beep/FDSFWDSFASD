package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class DrivePolicyTest {

    private static final long MIN = 60_000L;
    private static final long START = 1_000_000L;

    private static DrivePolicy.Decision check(boolean carConnected, long minutesSinceStart,
                                              long minutesSinceDriving) {
        long now = START + minutesSinceStart * MIN;
        long lastDriving = minutesSinceDriving < 0 ? -1 : now - minutesSinceDriving * MIN;
        return DrivePolicy.onWatchdog(carConnected, now, START, lastDriving);
    }

    @Test
    public void longTrafficJamWhileConnectedToCar_keepsTracking() {
        // błąd 1: 30 minut w korku, telefon cały czas połączony z autem
        assertEquals(DrivePolicy.Decision.CONTINUE, check(true, 60, 30));
    }

    @Test
    public void connectedButIdleForOverAnHour_endsAndSaves() {
        // radio auta zostaje włączone po zgaszeniu silnika: nie trzymaj GPS w nieskończoność
        assertEquals(DrivePolicy.Decision.END_AND_SAVE, check(true, 120, 61));
    }

    @Test
    public void disconnectedAfterIgnoredGlitch_endsFiveMinutesAfterLastDriving() {
        // błąd 2: Bluetooth zerwał się w trasie i nie wrócił, auto stoi od 6 minut
        assertEquals(DrivePolicy.Decision.END_AND_SAVE, check(false, 40, 6));
    }

    @Test
    public void disconnectedShortStop_keepsTracking() {
        // światła / krótki postój po zerwaniu Bluetooth
        assertEquals(DrivePolicy.Decision.CONTINUE, check(false, 40, 2));
    }

    @Test
    public void neverDrove_falseAlarmAfterTwentyMinutes() {
        assertEquals(DrivePolicy.Decision.END_WITHOUT_SAVE, check(false, 21, -1));
        assertEquals(DrivePolicy.Decision.CONTINUE, check(false, 10, -1));
    }

    @Test
    public void connectedButNeverDrove_waitsUpToAnHour() {
        // siedzisz w aucie z włączonym radiem, jeszcze nie ruszyłeś
        assertEquals(DrivePolicy.Decision.CONTINUE, check(true, 30, -1));
        assertEquals(DrivePolicy.Decision.END_WITHOUT_SAVE, check(true, 61, -1));
    }

    @Test
    public void blockedAlert_atMostOncePerDay() {
        long day = 24 * 60 * MIN;
        assertEquals(true, DrivePolicy.shouldAlertBlocked(0, 5 * day));        // jeszcze nie pokazano
        assertEquals(false, DrivePolicy.shouldAlertBlocked(5 * day, 5 * day + 3 * 60 * MIN));
        assertEquals(true, DrivePolicy.shouldAlertBlocked(5 * day, 6 * day + 1));
    }
}
