package pl.godziny.praca;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

/** Trwały zapis wpisów i ustawień (SharedPreferences, tylko na telefonie). */
public final class EntryStore {

    public static final long DEFAULT_RATE_CENTS = 3400; // $34.00/h

    static final String PREFS = "godziny";

    private static final String K_ENTRIES = "entries";
    private static final String K_NEXT_ID = "next_id";
    private static final String K_RATE = "rate_cents";
    private static final String K_FIRST_DAY = "first_day";
    private static final String K_OVERTIME = "overtime";

    private final SharedPreferences sp;

    public EntryStore(Context ctx) {
        sp = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    /** Wszystkie wpisy. Stare wpisy (bez zapisanej stawki) dostają bieżącą stawkę. */
    public List<Entry> all() {
        return Entry.decode(sp.getString(K_ENTRIES, ""), rateCents());
    }

    private void save(List<Entry> list) {
        sp.edit().putString(K_ENTRIES, Entry.encode(list)).apply();
    }

    private long nextId() {
        long id = sp.getLong(K_NEXT_ID, 1);
        sp.edit().putLong(K_NEXT_ID, id + 1).apply();
        return id;
    }

    /** Clock In (end == 0) albo wpis z zegara: zapis zegara = podane godziny. */
    public Entry add(long start, long end) {
        Entry e = new Entry(nextId(), start, end, 0, rateCents(), start, end, false);
        List<Entry> list = all();
        list.add(e);
        save(list);
        return e;
    }

    /** Wpis dodany ręcznie (nie z zegara). */
    public Entry addManual(long start, long end, int breakMin) {
        Entry e = new Entry(nextId(), start, end, breakMin, rateCents(), start, end, true);
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

    /** Usuwa podane wpisy (np. cały dzień). */
    public void deleteAll(java.util.Collection<Long> ids) {
        List<Entry> out = new ArrayList<>();
        for (Entry e : all()) if (!ids.contains(e.id)) out.add(e);
        save(out);
    }

    /** Przywraca usunięte wpisy (Cofnij). Identyfikatory nie są używane ponownie, więc nie kolidują. */
    public int restore(List<Entry> deleted) {
        List<Entry> list = all();
        java.util.Set<Long> have = new java.util.HashSet<>();
        boolean running = false;
        for (Entry e : list) {
            have.add(e.id);
            running |= e.isRunning();
        }
        int n = 0;
        for (Entry e : deleted) {
            if (have.contains(e.id)) continue;
            if (e.isRunning() && running) continue;   // tylko jedna trwająca zmiana naraz
            list.add(e);
            n++;
        }
        save(list);
        return n;
    }

    /** Podmienia wszystkie wpisy (przywracanie kopii z pliku CSV). */
    public void replaceAll(List<Entry> entries) {
        long max = 0;
        for (Entry e : entries) max = Math.max(max, e.id);
        save(entries);
        sp.edit().putLong(K_NEXT_ID, Math.max(max + 1, sp.getLong(K_NEXT_ID, 1))).apply();
    }

    public long rateCents() {
        return sp.getLong(K_RATE, DEFAULT_RATE_CENTS);
    }

    /**
     * Nowa stawka dla kolejnych wpisów. Wpisy zaczęte od {@code applyFrom} (np. początek
     * bieżącego tygodnia; {@code Long.MAX_VALUE} = żadne) też ją dostają; starsze zostają.
     */
    public void setRateCents(long cents, long applyFrom) {
        // Najpierw utrwal stare wpisy z dotychczasową stawką (stary format jej nie zapisywał).
        List<Entry> list = all();
        for (int i = 0; i < list.size(); i++) {
            if (list.get(i).start >= applyFrom) list.set(i, list.get(i).withRate(cents));
        }
        save(list);
        sp.edit().putLong(K_RATE, cents).apply();
    }

    /** Pierwszy dzień tygodnia roboczego: Calendar.MONDAY (domyślnie) … Calendar.SATURDAY. */
    public int firstDay() {
        return sp.getInt(K_FIRST_DAY, Calendar.MONDAY);
    }

    public void setFirstDay(int day) {
        sp.edit().putInt(K_FIRST_DAY, day).apply();
    }

    /** Nadgodziny FLSA (×1.5 ponad 40 h tygodniowo). Domyślnie włączone. */
    public boolean overtime() {
        return sp.getBoolean(K_OVERTIME, true);
    }

    public void setOvertime(boolean on) {
        sp.edit().putBoolean(K_OVERTIME, on).apply();
    }
}
