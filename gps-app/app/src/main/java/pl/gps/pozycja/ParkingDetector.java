package pl.gps.pozycja;

/**
 * Na podstawie kolejnych pomiarów GPS z jazdy ustala, gdzie auto zostało zaparkowane.
 *
 * <p>System zgłasza koniec jazdy z opóźnieniem (zwykle po 1–3 minutach), kiedy kierowca
 * może już odejść od auta. Dlatego nie bierzemy pozycji z chwili tego zgłoszenia, tylko
 * pierwszy pomiar, w którym auto stanęło po ostatnim odcinku jazdy. Chodzenie pieszo
 * (wolniej niż {@link #DRIVING_SPEED_MS}) tego punktu nie zmienia. Ponowna jazda
 * (np. po czerwonym świetle) go kasuje.
 *
 * <p>Klasa nie zależy od Androida, więc można ją testować zwykłym JUnitem.
 */
final class ParkingDetector {

    /** Pomiar pozycji. Prędkość NaN oznacza, że GPS jej nie podał. */
    static final class Fix {
        final double latitude, longitude;
        final float accuracy;
        final float speed;
        final long timeMs;

        Fix(double latitude, double longitude, float accuracy, float speed, long timeMs) {
            this.latitude = latitude;
            this.longitude = longitude;
            this.accuracy = accuracy;
            this.speed = speed;
            this.timeMs = timeMs;
        }
    }

    /** Powyżej tej prędkości (ok. 15 km/h) to na pewno jazda, a nie spacer. */
    static final float DRIVING_SPEED_MS = 4.2f;
    /** Poniżej tej prędkości (ok. 3,6 km/h) auto uznajemy za stojące. */
    static final float STOPPED_SPEED_MS = 1.0f;
    /** Pomiary mniej dokładne niż to pomijamy przy wyborze miejsca postoju. */
    static final float MAX_ACCURACY_M = 50f;

    private Fix last;
    private Fix lastDriving;
    private Fix stopCandidate;

    void reset() {
        last = lastDriving = stopCandidate = null;
    }

    void add(Fix fix) {
        float speed = Float.isNaN(fix.speed) ? speedFromPrevious(fix) : fix.speed;
        last = fix;
        if (Float.isNaN(speed)) return;

        if (speed >= DRIVING_SPEED_MS) {
            lastDriving = fix;
            stopCandidate = null; // znów jedziemy: poprzedni postój to tylko światła / korek
        } else if (lastDriving != null && stopCandidate == null
                && speed < STOPPED_SPEED_MS && fix.accuracy <= MAX_ACCURACY_M) {
            stopCandidate = fix;
        }
    }

    private float speedFromPrevious(Fix fix) {
        if (last == null || fix.timeMs <= last.timeMs) return Float.NaN;
        double d = Geo.distanceMeters(last.latitude, last.longitude, fix.latitude, fix.longitude);
        return (float) (d / ((fix.timeMs - last.timeMs) / 1000.0));
    }

    /** Czy w tej sesji była już prawdziwa jazda (a nie tylko fałszywy alarm). */
    boolean hasDriven() {
        return lastDriving != null;
    }

    /** Czas ostatniego pomiaru z prędkością jazdy albo -1, jeśli jazdy jeszcze nie było. */
    long lastDrivingTimeMs() {
        return lastDriving == null ? -1 : lastDriving.timeMs;
    }

    Fix lastFix() {
        return last;
    }

    /**
     * Najlepsze przybliżenie miejsca parkowania: pierwszy postój po ostatniej jeździe,
     * a gdy go brak, ostatni punkt jazdy, a gdy i tego brak, ostatni pomiar.
     */
    Fix parkingFix() {
        if (stopCandidate != null) return stopCandidate;
        if (lastDriving != null) return lastDriving;
        return last;
    }
}
