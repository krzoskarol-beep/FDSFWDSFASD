package pl.godziny.praca;

import java.util.ArrayList;
import java.util.List;

/** Jeden wpis czasu pracy. {@code end == 0} oznacza zmianę w trakcie (po Clock In). */
public final class Entry {
    public final long id;
    public final long start;
    public final long end;

    public Entry(long id, long start, long end) {
        this.id = id;
        this.start = start;
        this.end = end;
    }

    public boolean isRunning() {
        return end == 0;
    }

    /** Koniec wpisu; dla trwającej zmiany — chwila {@code now}. */
    public long endOr(long now) {
        return isRunning() ? Math.max(now, start) : end;
    }

    public Entry withTimes(long newStart, long newEnd) {
        return new Entry(id, newStart, newEnd);
    }

    // ------------------------------------------------------------ zapis: "id,start,end" w liniach

    public static String encode(List<Entry> list) {
        StringBuilder sb = new StringBuilder();
        for (Entry e : list) {
            sb.append(e.id).append(',').append(e.start).append(',').append(e.end).append('\n');
        }
        return sb.toString();
    }

    /** Odczyt odporny na uszkodzone linie (są pomijane). */
    public static List<Entry> decode(String text) {
        List<Entry> out = new ArrayList<>();
        if (text == null) return out;
        for (String line : text.split("\n")) {
            String[] p = line.trim().split(",");
            if (p.length != 3) continue;
            try {
                long id = Long.parseLong(p[0]);
                long s = Long.parseLong(p[1]);
                long e = Long.parseLong(p[2]);
                if (s <= 0 || e < 0 || (e != 0 && e < s)) continue;
                out.add(new Entry(id, s, e));
            } catch (NumberFormatException ignored) {
                // pomiń
            }
        }
        return out;
    }
}
