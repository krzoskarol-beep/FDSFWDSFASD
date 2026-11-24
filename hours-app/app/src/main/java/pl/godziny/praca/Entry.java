package pl.godziny.praca;

import java.util.ArrayList;
import java.util.List;

/**
 * Jeden wpis czasu pracy. {@code end == 0} oznacza zmianę w trakcie (po Clock In).
 *
 * Wpis pamięta też to, czego nie wolno zgubić przy edycji:
 * <ul>
 *   <li>{@code rateCents} — stawkę z chwili pracy (zmiana stawki nie przelicza historii),</li>
 *   <li>{@code breakMin} — bezpłatną przerwę na posiłek (29 CFR 785.19), odejmowaną od czasu,</li>
 *   <li>{@code origStart}/{@code origEnd} — godziny z zegara (Clock In / Clock Out); różnica
 *       względem start/end oznacza ręczną poprawkę. {@code origEnd == 0}: brak Clock Out.</li>
 *   <li>{@code manual} — wpis dodany ręcznie, a nie z zegara.</li>
 * </ul>
 */
public final class Entry {

    /** Stawka dla starych wpisów bez zapisanej stawki (wersje 1.0–1.2) i dla testów. */
    public static final long LEGACY_RATE_CENTS = 3400;

    public final long id;
    public final long start;
    public final long end;
    public final int breakMin;
    public final long rateCents;
    public final long origStart;
    public final long origEnd;
    public final boolean manual;

    public Entry(long id, long start, long end, int breakMin, long rateCents,
                 long origStart, long origEnd, boolean manual) {
        this.id = id;
        this.start = start;
        this.end = end;
        this.breakMin = Math.max(0, breakMin);
        this.rateCents = rateCents;
        this.origStart = origStart;
        this.origEnd = origEnd;
        this.manual = manual;
    }

    /** Wpis z zegara bez przerwy, stawka $34 (skrót dla testów i starych danych). */
    public Entry(long id, long start, long end) {
        this(id, start, end, 0, LEGACY_RATE_CENTS, start, end, false);
    }

    public boolean isRunning() {
        return end == 0;
    }

    /** Koniec wpisu; dla trwającej zmiany — chwila {@code now}. */
    public long endOr(long now) {
        return isRunning() ? Math.max(now, start) : end;
    }

    /** Godziny różnią się od zapisu zegara (albo wpis jest ręczny). */
    public boolean isEdited() {
        if (manual) return true;
        if (start != origStart) return true;
        return !isRunning() && end != origEnd;
    }

    public Entry withTimes(long newStart, long newEnd) {
        return new Entry(id, newStart, newEnd, breakMin, rateCents, origStart, origEnd, manual);
    }

    public Entry withBreak(int minutes) {
        return new Entry(id, start, end, minutes, rateCents, origStart, origEnd, manual);
    }

    public Entry withRate(long cents) {
        return new Entry(id, start, end, breakMin, cents, origStart, origEnd, manual);
    }

    /** Clock Out: koniec i zapis zegara jednocześnie. */
    public Entry clockedOut(long at) {
        return new Entry(id, start, at, breakMin, rateCents, origStart, at, manual);
    }

    // ------------------------------------------------------------ zapis w SharedPreferences
    // Linia: id,start,end,przerwa,stawka,zegarStart,zegarKoniec,ręczny(0/1).
    // Stary format (wersje 1.0–1.2) miał tylko id,start,end — wczytuje się jako wpis z zegara.

    public static String encode(List<Entry> list) {
        StringBuilder sb = new StringBuilder();
        for (Entry e : list) {
            sb.append(e.id).append(',').append(e.start).append(',').append(e.end).append(',')
                    .append(e.breakMin).append(',').append(e.rateCents).append(',')
                    .append(e.origStart).append(',').append(e.origEnd).append(',')
                    .append(e.manual ? 1 : 0).append('\n');
        }
        return sb.toString();
    }

    /** Odczyt odporny na uszkodzone linie (są pomijane). */
    public static List<Entry> decode(String text, long legacyRateCents) {
        List<Entry> out = new ArrayList<>();
        if (text == null) return out;
        for (String line : text.split("\n")) {
            String[] p = line.trim().split(",");
            try {
                Entry e;
                if (p.length == 3) {
                    long s = Long.parseLong(p[1]);
                    long en = Long.parseLong(p[2]);
                    e = new Entry(Long.parseLong(p[0]), s, en, 0, legacyRateCents, s, en, false);
                } else if (p.length == 8) {
                    e = new Entry(Long.parseLong(p[0]), Long.parseLong(p[1]), Long.parseLong(p[2]),
                            Integer.parseInt(p[3]), Long.parseLong(p[4]), Long.parseLong(p[5]),
                            Long.parseLong(p[6]), "1".equals(p[7]));
                } else {
                    continue;
                }
                if (isValid(e)) out.add(e);
            } catch (NumberFormatException ignored) {
                // pomiń
            }
        }
        return out;
    }

    static boolean isValid(Entry e) {
        return e.start > 0 && e.end >= 0 && (e.end == 0 || e.end >= e.start)
                && e.rateCents > 0 && e.breakMin >= 0;
    }
}
