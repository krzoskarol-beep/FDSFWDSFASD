package pl.godziny.praca;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

/** Trwały zapis wpisów i ustawień (SharedPreferences, tylko na telefonie). */
public final class EntryStore {

    public static final long DEFAULT_RATE_CENTS = 3400; // $34.00/h

    private static final String K_ENTRIES = "entries";
    private static final String K_NEXT_ID = "next_id";
    private static final String K_RATE = "rate_cents";
    private static final String K_FIRST_DAY = "first_day";

    private final SharedPreferences sp;

    public EntryStore(Context ctx) {
        sp = ctx.getSharedPreferences("godziny", Context.MODE_PRIVATE);
    }

    public List<Entry> all() {
        return Entry.decode(sp.getString(K_ENTRIES, ""));
    }

    private void save(List<Entry> list) {
        sp.edit().putString(K_ENTRIES, Entry.encode(list)).apply();
    }

    public Entry add(long start, long end) {
        long id = sp.getLong(K_NEXT_ID, 1);
        sp.edit().putLong(K_NEXT_ID, id + 1).apply();
        Entry e = new Entry(id, start, end);
        List<Entry> list = all();
        list.add(e);
        save(list);
        return e;
    }

    public void update(Entry changed) {
        List<Entry> list = all();
        for (int i = 0; i < list.size(); i++) {
            if (list.get(i).id == changed.id) list.set(i, changed);
        }
        save(list);
    }

    public void delete(long id) {
        List<Entry> out = new ArrayList<>();
        for (Entry e : all()) if (e.id != id) out.add(e);
        save(out);
    }

    public long rateCents() {
        return sp.getLong(K_RATE, DEFAULT_RATE_CENTS);
    }

    public void setRateCents(long cents) {
        sp.edit().putLong(K_RATE, cents).apply();
    }

    /** Calendar.MONDAY (domyślnie) albo Calendar.SUNDAY. */
    public int firstDay() {
        return sp.getInt(K_FIRST_DAY, Calendar.MONDAY);
    }

    public void setFirstDay(int day) {
        sp.edit().putInt(K_FIRST_DAY, day).apply();
    }
}
