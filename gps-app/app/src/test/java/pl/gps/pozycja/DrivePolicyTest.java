package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class DrivePolicyTest {

    private static final long MIN = 60_000L;
    private static final long START = 1_000_000L;

    private static DrivePolicy.Decision check(boolean inVehicle, long minutesSinceStart,
                                              long minutesSinceDriving) {
        long now = START + minutesSinceStart * MIN;
        long lastDriving = minutesSinceDriving < 0 ? -1 : now - minutesSinceDriving * MIN;
        return DrivePolicy.onWatchdog(inVehicle, now, START, lastDriving);
    }

    @Test
    public void longTrafficJamWhileInVehicle_keepsTracking() {
        // 30 minut w korku, Google cały czas widzi pojazd
        assertEquals(DrivePolicy.Decision.CONTINUE, check(true, 60, 30));
    }

    @Test
    public void inVehicleButIdleForOverAnHour_endsAndSaves() {
        // bez ruchu ponad godzinę: nie trzymaj GPS w nieskończoność
        assertEquals(DrivePolicy.Decision.END_AND_SAVE, check(true, 120, 61));
    }

    @Test
    public void outOfVehicleAfterResumedExit_endsFiveMinutesAfterLastDriving() {
        // zgłoszony koniec jazdy odrzucony (auto ruszyło), potem postój 6 minut bez nowego zgłoszenia
        assertEquals(DrivePolicy.Decision.END_AND_SAVE, check(false, 40, 6));
    }

    @Test
    public void outOfVehicleShortStop_keepsTracking() {
        // światła / krótki postój
        assertEquals(DrivePolicy.Decision.CONTINUE, check(false, 40, 2));
    }

    @Test
    public void neverDrove_falseAlarmAfterTwentyMinutes() {
        assertEquals(DrivePolicy.Decision.END_WITHOUT_SAVE, check(false, 21, -1));
        assertEquals(DrivePolicy.Decision.CONTINUE, check(false, 10, -1));
    }

    @Test
    public void inVehicleButNeverDrove_waitsUpToAnHour() {
        // Google widzi pojazd, ale GPS jeszcze nie zarejestrował jazdy
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

    // --- potwierdzanie końca jazdy zgłoszonego przez usługi Google

    private static DrivePolicy.ExitDecision exit(long minutesSinceExit, long minutesSinceDriving) {
        long now = START + 100 * MIN;
        long exitAt = now - minutesSinceExit * MIN;
        long lastDriving = minutesSinceDriving < 0 ? -1 : now - minutesSinceDriving * MIN;
        return DrivePolicy.onExitGrace(exitAt, now, lastDriving);
    }

    @Test
    public void exitInTrafficJam_drivingResumes_isNotParking() {
        // Google zgłosił koniec jazdy 2 min temu, ale minutę temu auto znów jechało
        assertEquals(DrivePolicy.ExitDecision.RESUMED, exit(2, 1));
    }

    @Test
    public void exitConfirmedAfterThreeMinutesWithoutDriving() {
        assertEquals(DrivePolicy.ExitDecision.CONFIRMED, exit(3, 5));
    }

    @Test
    public void exitWaitsDuringGracePeriod() {
        assertEquals(DrivePolicy.ExitDecision.WAIT, exit(1, 4));
    }

    @Test
    public void lateDeliveredExitIsConfirmedImmediately() {
        // zdarzenie dotarło z opóźnieniem: koniec jazdy był 10 min temu, od tamtej pory bez jazdy
        assertEquals(DrivePolicy.ExitDecision.CONFIRMED, exit(10, 12));
    }

    @Test
    public void exitWithoutAnyDrivingDataIsConfirmedAfterGrace() {
        assertEquals(DrivePolicy.ExitDecision.CONFIRMED, exit(3, -1));
        assertEquals(DrivePolicy.ExitDecision.WAIT, exit(0, -1));
    }
}
