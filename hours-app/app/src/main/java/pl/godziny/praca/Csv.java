package pl.godziny.praca;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;

/**
 * Eksport i import wpisów w CSV. Plik służy jednocześnie jako:
 * <ul>
 *   <li>ewidencja czytelna w arkuszu (data, godziny, przerwa, minuty, stawka, kwota),</li>
 *   <li>kopia zapasowa — kolumny *_ms przechowują dokładne znaczniki czasu, więc import
 *       odtwarza wpisy 1:1, łącznie ze śladem zegara.</li>
 * </ul>
 * Kwota w wierszu = minuty × stawka / 60.
 */
public final class Csv {

    static final String[] HEADER = {"data", "dzien", "poczatek", "koniec", "przerwa_min",
            "minuty_platne", "godziny_dziesietnie", "stawka_usd", "kwota_usd", "zrodlo",
            "zegar_poczatek", "zegar_koniec", "id", "start_ms", "end_ms", "zegar_start_ms",
            "zegar_koniec_ms"};

    static final String SRC_CLOCK = "zegar";
    static final String SRC_EDITED = "zegar+poprawka";
    static final String SRC_MANUAL = "reczny";

    private Csv() {}

    public static String export(List<Entry> all, long now, TimeZone tz) {
        List<Entry> list = new ArrayList<>(all);
        Collections.sort(list, (a, b) -> Long.compare(a.start, b.start));
        SimpleDateFormat date = Report.fmt("yyyy-MM-dd", tz);
        SimpleDateFormat hm = Report.fmt("HH:mm", tz);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < HEADER.length; i++) sb.append(i == 0 ? "" : ",").append(HEADER[i]);
        sb.append('\n');   // (String.join jest dopiero od Androida 8)
        for (Entry e : list) {
            long min = WorkMath.minutes(e, now);
            String src = e.manual ? SRC_MANUAL : e.isEdited() ? SRC_EDITED : SRC_CLOCK;
            sb.append(date.format(e.start)).append(',')
                    .append(Report.dayShort(e.start, tz)).append(',')
                    .append(hm.format(e.start)).append(',')
                    .append(e.isRunning() ? "" : hm.format(e.end)).append(',')
                    .append(e.breakMin).append(',')
                    .append(min).append(',')
                    .append(WorkMath.formatDecimalHours(min)).append(',')
                    .append(plain(e.rateCents)).append(',')
                    .append(plain(WorkMath.payCents(min, e.rateCents))).append(',')
                    .append(src).append(',')
                    .append(e.manual ? "" : hm.format(e.origStart)).append(',')
                    .append(e.manual || e.origEnd == 0 ? "" : hm.format(e.origEnd)).append(',')
                    .append(e.id).append(',')
                    .append(e.start).append(',')
                    .append(e.end).append(',')
                    .append(e.origStart).append(',')
                    .append(e.origEnd).append('\n');
        }
        return sb.toString();
    }

    /** "1096.50" — kwota bez znaku dolara i separatorów tysięcy (dla arkuszy). */
    static String plain(long cents) {
        return String.format(Locale.US, "%d.%02d", cents / 100, cents % 100);
    }

    /** Wynik importu: wpisy albo opis pierwszego błędu. */
    public static final class Result {
        public final List<Entry> entries;
        public final String error;

        Result(List<Entry> entries, String error) {
            this.entries = entries;
            this.error = error;
        }
    }

    public static Result parse(String text) {
        if (text == null || text.trim().isEmpty()) return fail("Plik jest pusty.");
        String[] lines = text.replace("\r", "").split("\n");
        String head = !lines[0].isEmpty() && lines[0].charAt(0) == 0xFEFF ? lines[0].substring(1) : lines[0];
        Map<String, Integer> col = new HashMap<>();
        String[] names = head.split(",", -1);
        for (int i = 0; i < names.length; i++) col.put(names[i].trim(), i);
        for (String need : new String[]{"id", "start_ms", "end_ms", "przerwa_min", "stawka_usd",
                "zrodlo", "zegar_start_ms", "zegar_koniec_ms"}) {
            if (!col.containsKey(need)) return fail("To nie jest kopia z tej aplikacji (brak kolumny " + need + ").");
        }
        List<Entry> out = new ArrayList<>();
        Set<Long> ids = new HashSet<>();
        int running = 0;
        for (int n = 1; n < lines.length; n++) {
            if (lines[n].trim().isEmpty()) continue;
            String[] p = lines[n].split(",", -1);
            String where = "Wiersz " + (n + 1) + ": ";
            try {
                long rate = WorkMath.parseRate(p[col.get("stawka_usd")]);
                if (rate <= 0) return fail(where + "błędna stawka.");
                long start = Long.parseLong(p[col.get("start_ms")].trim());
                long end = Long.parseLong(p[col.get("end_ms")].trim());
                Entry e = new Entry(Long.parseLong(p[col.get("id")].trim()), start, end,
                        Integer.parseInt(p[col.get("przerwa_min")].trim()), rate,
                        Long.parseLong(p[col.get("zegar_start_ms")].trim()),
                        Long.parseLong(p[col.get("zegar_koniec_ms")].trim()),
                        SRC_MANUAL.equals(p[col.get("zrodlo")].trim()));
                if (!Entry.isValid(e)) return fail(where + "błędne godziny.");
                if (end != 0 && end - start > WorkMath.MAX_ENTRY) return fail(where + "wpis dłuższy niż 24 h.");
                if (!ids.add(e.id)) return fail(where + "powtórzony identyfikator.");
                if (e.isRunning() && ++running > 1) return fail(where + "więcej niż jedna trwająca zmiana.");
                out.add(e);
            } catch (RuntimeException ex) {   // NumberFormat, brak kolumny w wierszu
                return fail(where + "nie da się odczytać.");
            }
        }
        return new Result(out, null);
    }

    private static Result fail(String msg) {
        return new Result(Collections.emptyList(), msg);
    }
}
