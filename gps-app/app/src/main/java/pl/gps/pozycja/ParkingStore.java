package pl.gps.pozycja;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/**
 * Przechowuje zapisane miejsce parkowania i historię ostatnich miejsc
 * w pamięci telefonu (przetrwa zamknięcie aplikacji).
 */
final class ParkingStore {

    static final class Spot {
        final double latitude;
        final double longitude;
        /** Dokładność pomiaru w chwili zapisu, w metrach (0 = nieznana). */
        final float accuracy;
        /** Czas zapisu, System.currentTimeMillis(). Służy też jako identyfikator wpisu. */
        final long savedAt;
        final String note;
        /** Adres ustalony po zapisie (np. „Marszałkowska 10, Warszawa”), pusty, jeśli nieznany. */
        final String address;

        Spot(double latitude, double longitude, float accuracy, long savedAt, String note) {
            this(latitude, longitude, accuracy, savedAt, note, "");
        }

        Spot(double latitude, double longitude, float accuracy, long savedAt, String note, String address) {
            this.latitude = latitude;
            this.longitude = longitude;
            this.accuracy = accuracy;
            this.savedAt = savedAt;
            this.note = note == null ? "" : note;
            this.address = address == null ? "" : address;
        }

        Spot withAddress(String newAddress) {
            return new Spot(latitude, longitude, accuracy, savedAt, note, newAddress);
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("lat", latitude).put("lon", longitude).put("acc", (double) accuracy)
                    .put("time", savedAt).put("note", note).put("addr", address);
        }

        static Spot fromJson(JSONObject o) {
            return new Spot(o.optDouble("lat"), o.optDouble("lon"), (float) o.optDouble("acc", 0),
                    o.optLong("time"), o.optString("note", ""), o.optString("addr", ""));
        }
    }

    /** Ile ostatnich miejsc pamięta historia. */
    static final int HISTORY_SIZE = 30;

    private static final String PREFS = "parking";
    private static final String K_LAT = "lat", K_LON = "lon", K_ACC = "acc", K_TIME = "time",
            K_NOTE = "note", K_ADDR = "addr", K_HISTORY = "history";

    private final SharedPreferences prefs;

    ParkingStore(Context context) {
        prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    // ------------------------------------------------------------------ aktualne miejsce

    Spot load() {
        if (!prefs.contains(K_LAT) || !prefs.contains(K_LON)) return null;
        return new Spot(
                Double.longBitsToDouble(prefs.getLong(K_LAT, 0)),
                Double.longBitsToDouble(prefs.getLong(K_LON, 0)),
                prefs.getFloat(K_ACC, 0f),
                prefs.getLong(K_TIME, 0),
                prefs.getString(K_NOTE, ""),
                prefs.getString(K_ADDR, ""));
    }

    /** Zapisuje nowe miejsce jako aktualne i dopisuje je na początek historii. */
    synchronized void save(Spot spot) {
        List<Spot> history = history();
        removeBySavedAt(history, spot.savedAt);
        history.add(0, spot);
        writeCurrent(prefs.edit(), spot).putString(K_HISTORY, toJson(history)).apply();
    }

    /** Przywraca miejsce z historii jako aktualne (bez dublowania wpisu w historii). */
    synchronized void restore(Spot spot) {
        writeCurrent(prefs.edit(), spot).apply();
    }

    /** Usuwa aktualne miejsce; historia zostaje. */
    synchronized void clear() {
        prefs.edit().remove(K_LAT).remove(K_LON).remove(K_ACC).remove(K_TIME)
                .remove(K_NOTE).remove(K_ADDR).apply();
    }

    /**
     * Dopisuje adres do miejsca zapisanego o {@code savedAt} (w aktualnym miejscu i w historii).
     * Adres przychodzi kilka sekund po zapisie; jeśli w międzyczasie zapisano nowe miejsce,
     * aktualne miejsce nie jest zmieniane.
     */
    synchronized void setAddress(long savedAt, String address) {
        SharedPreferences.Editor e = prefs.edit();
        Spot current = load();
        if (current != null && current.savedAt == savedAt) e.putString(K_ADDR, address);
        List<Spot> history = history();
        for (int i = 0; i < history.size(); i++) {
            if (history.get(i).savedAt == savedAt) history.set(i, history.get(i).withAddress(address));
        }
        e.putString(K_HISTORY, toJson(history)).apply();
    }

    private static SharedPreferences.Editor writeCurrent(SharedPreferences.Editor e, Spot spot) {
        return e.putLong(K_LAT, Double.doubleToRawLongBits(spot.latitude))
                .putLong(K_LON, Double.doubleToRawLongBits(spot.longitude))
                .putFloat(K_ACC, spot.accuracy)
                .putLong(K_TIME, spot.savedAt)
                .putString(K_NOTE, spot.note)
                .putString(K_ADDR, spot.address);
    }

    // ------------------------------------------------------------------ historia

    /** Historia od najnowszego miejsca. */
    List<Spot> history() {
        List<Spot> out = new ArrayList<>();
        String raw = prefs.getString(K_HISTORY, null);
        if (raw == null) return out;
        try {
            JSONArray a = new JSONArray(raw);
            for (int i = 0; i < a.length(); i++) out.add(Spot.fromJson(a.getJSONObject(i)));
        } catch (JSONException ignored) {
            // uszkodzona historia: zaczynamy od nowa
        }
        return out;
    }

    synchronized void removeFromHistory(long savedAt) {
        List<Spot> history = history();
        removeBySavedAt(history, savedAt);
        prefs.edit().putString(K_HISTORY, toJson(history)).apply();
    }

    synchronized void clearHistory() {
        prefs.edit().remove(K_HISTORY).apply();
    }

    private static void removeBySavedAt(List<Spot> list, long savedAt) {
        for (int i = list.size() - 1; i >= 0; i--) {
            if (list.get(i).savedAt == savedAt) list.remove(i);
        }
    }

    private static String toJson(List<Spot> history) {
        JSONArray a = new JSONArray();
        for (int i = 0; i < history.size() && i < HISTORY_SIZE; i++) {
            try {
                a.put(history.get(i).toJson());
            } catch (JSONException ignored) {
                // pomijamy wpis, którego nie da się zapisać (np. NaN)
            }
        }
        return a.toString();
    }

    // ------------------------------------------------------------------ powiadomienia o zmianach

    /** Powiadamia o zmianie zapisanego miejsca (np. gdy zapisze je usługa w tle). */
    void addListener(SharedPreferences.OnSharedPreferenceChangeListener l) {
        prefs.registerOnSharedPreferenceChangeListener(l);
    }

    void removeListener(SharedPreferences.OnSharedPreferenceChangeListener l) {
        prefs.unregisterOnSharedPreferenceChangeListener(l);
    }
}
