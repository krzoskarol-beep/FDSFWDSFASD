package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class ParkingDetectorTest {

    private final ParkingDetector detector = new ParkingDetector();
    private long t = 0;
    private double lat = 52.0;

    /** Dodaje pomiar, przesuwając się na północ o tyle, ile wynika z prędkości. */
    private ParkingDetector.Fix step(float speedMs) {
        return stepWith(speedMs, 10f, speedMs);
    }

    private ParkingDetector.Fix stepWith(float movedSpeedMs, float accuracy, float reportedSpeed) {
        t += 1000;
        lat += movedSpeedMs / 111_195.0; // metry na stopień szerokości
        ParkingDetector.Fix f = new ParkingDetector.Fix(lat, 21.0, accuracy, reportedSpeed, t);
        detector.add(f);
        return f;
    }

    @Test
    public void emptyDetectorHasNoParking() {
        assertNull(detector.parkingFix());
        assertFalse(detector.hasDriven());
    }

    @Test
    public void parkingIsWhereCarStopped_notWhereDriverWalkedTo() {
        for (int i = 0; i < 30; i++) step(14f);   // jazda ok. 50 km/h
        for (int i = 0; i < 5; i++) step(2f);     // manewry na parkingu
        ParkingDetector.Fix parked = step(0.1f);  // auto stoi
        for (int i = 0; i < 10; i++) step(0.2f);
        for (int i = 0; i < 90; i++) step(1.4f);  // kierowca odchodzi pieszo

        assertTrue(detector.hasDriven());
        assertSame(parked, detector.parkingFix());
    }

    @Test
    public void stopAtTrafficLightIsForgottenWhenDrivingResumes() {
        for (int i = 0; i < 20; i++) step(14f);
        for (int i = 0; i < 30; i++) step(0f);    // czerwone światło
        for (int i = 0; i < 20; i++) step(12f);   // jedziemy dalej
        ParkingDetector.Fix parked = step(0.3f);
        for (int i = 0; i < 20; i++) step(1.3f);

        assertSame(parked, detector.parkingFix());
    }

    @Test
    public void inaccurateStopFixIsSkipped() {
        for (int i = 0; i < 20; i++) step(14f);
        stepWith(0f, 120f, 0f);                   // pomiar z błędem 120 m
        ParkingDetector.Fix good = step(0.2f);

        assertSame(good, detector.parkingFix());
    }

    @Test
    public void lostGpsInUndergroundGarageFallsBackToLastDrivingPoint() {
        for (int i = 0; i < 20; i++) step(14f);
        ParkingDetector.Fix entrance = step(5f);  // wjazd do garażu, potem brak sygnału

        assertSame(entrance, detector.parkingFix());
    }

    @Test
    public void walkingOnlyIsNotDriving() {
        for (int i = 0; i < 60; i++) step(1.5f);
        assertFalse(detector.hasDriven());
        assertEquals(-1, detector.lastDrivingTimeMs());
        assertSame(detector.lastFix(), detector.parkingFix());
    }

    @Test
    public void speedIsComputedWhenGpsDoesNotReportIt() {
        for (int i = 0; i < 10; i++) stepWith(14f, 10f, Float.NaN);
        assertTrue(detector.hasDriven());
        ParkingDetector.Fix parked = stepWith(0f, 10f, Float.NaN);
        stepWith(1.2f, 10f, Float.NaN);

        assertSame(parked, detector.parkingFix());
    }

    @Test
    public void resetForgetsEverything() {
        for (int i = 0; i < 10; i++) step(14f);
        detector.reset();
        assertNull(detector.parkingFix());
        assertFalse(detector.hasDriven());
    }

    // --- pozycja z chwili zdarzenia (Bluetooth auta)

    @Test
    public void fixAt_returnsPositionAtEngineOff_notAfterwards() {
        for (int i = 0; i < 20; i++) step(14f);
        for (int i = 0; i < 4; i++) step(2f);     // dojazd na miejsce
        ParkingDetector.Fix engineOff = step(0f);
        long eventTime = t;                       // w tej chwili rozłączył się Bluetooth
        for (int i = 0; i < 30; i++) step(1.4f);  // kierowca odchodzi (pomiary po zdarzeniu)

        assertSame(engineOff, detector.fixAt(eventTime, 30_000));
    }

    @Test
    public void fixAt_tooOldReturnsNull() {
        step(14f);
        assertNull(detector.fixAt(t + 60_000, 30_000));
    }

    @Test
    public void fixAt_skipsInaccurateFixes() {
        ParkingDetector.Fix good = step(0f);
        stepWith(0f, 200f, 0f);
        assertSame(good, detector.fixAt(t, 30_000));
    }

    @Test
    public void fixAt_emptyHistory() {
        assertNull(detector.fixAt(1000, 30_000));
    }

    @Test
    public void historyIsBounded() {
        for (int i = 0; i < ParkingDetector.HISTORY_SIZE + 50; i++) step(0f);
        // najstarszych pomiarów już nie ma
        assertNull(detector.fixAt(1000, 1000));
        assertSame(detector.lastFix(), detector.fixAt(t, 1000));
    }

    @Test
    public void isMovingAt_distinguishesBluetoothGlitchFromParking() {
        for (int i = 0; i < 20; i++) step(20f);
        assertTrue("rozłączenie w trasie", detector.isMovingAt(t, 10_000));
        for (int i = 0; i < 5; i++) step(0f);
        assertFalse("auto stoi", detector.isMovingAt(t, 10_000));
    }
}
