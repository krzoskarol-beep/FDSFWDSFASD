package pl.gps.pozycja;

import android.content.Context;
import android.content.SharedPreferences;

/** Przechowuje zapisane miejsce parkowania w pamięci telefonu (przetrwa zamknięcie aplikacji). */
final class ParkingStore {

    static final class Spot {
        final double latitude;
        final double longitude;
        /** Dokładność pomiaru w chwili zapisu, w metrach (0 = nieznana). */
        final float accuracy;
        /** Czas zapisu, System.currentTimeMillis(). */
        final long savedAt;
        final String note;

        Spot(double latitude, double longitude, float accuracy, long savedAt, String note) {
            this.latitude = latitude;
            this.longitude = longitude;
            this.accuracy = accuracy;
            this.savedAt = savedAt;
            this.note = note == null ? "" : note;
        }
    }

    private static final String PREFS = "parking";
    private static final String K_LAT = "lat", K_LON = "lon", K_ACC = "acc", K_TIME = "time", K_NOTE = "note";

    private final SharedPreferences prefs;

    ParkingStore(Context context) {
        prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    Spot load() {
        if (!prefs.contains(K_LAT) || !prefs.contains(K_LON)) return null;
        return new Spot(
                Double.longBitsToDouble(prefs.getLong(K_LAT, 0)),
                Double.longBitsToDouble(prefs.getLong(K_LON, 0)),
                prefs.getFloat(K_ACC, 0f),
                prefs.getLong(K_TIME, 0),
                prefs.getString(K_NOTE, ""));
    }

    void save(Spot spot) {
        prefs.edit()
                .putLong(K_LAT, Double.doubleToRawLongBits(spot.latitude))
                .putLong(K_LON, Double.doubleToRawLongBits(spot.longitude))
                .putFloat(K_ACC, spot.accuracy)
                .putLong(K_TIME, spot.savedAt)
                .putString(K_NOTE, spot.note)
                .apply();
    }

    void clear() {
        prefs.edit().clear().apply();
    }
}
