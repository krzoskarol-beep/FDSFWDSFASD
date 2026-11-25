package pl.godziny.praca;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

/** Tekst raportu tygodniowego (do podglądu, kopiowania i udostępnienia). */
public final class Report {

    static final String[] DAYS = {"", "Nd", "Pn", "Wt", "Śr", "Cz", "Pt", "Sb"};
    /** Pełne nazwy dni, indeks = Calendar.DAY_OF_WEEK. */
    static final String[] DAYS_FULL = {"", "niedziela", "poniedziałek", "wtorek", "środa",
            "czwartek", "piątek", "sobota"};

    private Report() {}

    public static String dayShort(long t, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(t);
        return DAYS[c.get(Calendar.DAY_OF_WEEK)];
    }

    /** "17.11 – 23.11.2026" */
    public static String weekLabel(long weekStart, TimeZone tz) {
        long last = WorkMath.addDays(weekStart, 6, tz);
        SimpleDateFormat dm = fmt("dd.MM", tz);
        SimpleDateFormat dmy = fmt("dd.MM.yyyy", tz);
        return dm.format(weekStart) + " – " + dmy.format(last);
    }

    /** Krótki opis szczegółów wpisu: przerwa i ślad poprawek; pusty, gdy nic do dodania. */
    public static String notes(Entry e, TimeZone tz) {
        SimpleDateFormat hm = fmt("HH:mm", tz);
        StringBuilder sb = new StringBuilder();
        if (e.breakMin > 0) sb.append("przerwa ").append(WorkMath.formatHm(e.breakMin));
        if (e.manual) {
            if (sb.length() > 0) sb.append("; ");
            sb.append("dodano ręcznie");
        } else if (e.isEdited()) {
            if (sb.length() > 0) sb.append("; ");
            sb.append("poprawiono, zegar: ").append(hm.format(e.origStart)).append("–")
                    .append(e.origEnd == 0 ? "brak Clock Out" : hm.format(e.origEnd));
        }
        return sb.toString();
    }

    public static String build(List<Entry> week, long weekStart, long now, TimeZone tz) {
        StringBuilder sb = new StringBuilder();
        sb.append("RAPORT TYGODNIOWY — GODZINY PRACY\n");
        sb.append("Tydzień: ").append(weekLabel(weekStart, tz)).append('\n');
        sb.append("Początek tygodnia: ").append(DAYS_FULL[dayOfWeek(weekStart, tz)]).append(", 00:00\n\n");
        if (week.isEmpty()) sb.append("Brak wpisów w tym tygodniu.\n");
        appendRows(sb, week, now, tz);
        appendTotals(sb, week, now, tz);
        return sb.toString();
    }

    static final String[] MONTHS = {"styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
            "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"};

    /** Północ 1. dnia miesiąca zawierającego {@code t}. */
    public static long monthStart(long t, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(WorkMath.dayStart(t, tz));
        c.set(Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }

    public static long addMonths(long monthStart, int n, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(monthStart);
        c.add(Calendar.MONTH, n);
        return c.getTimeInMillis();
    }

    /** "listopad 2026" */
    public static String monthLabel(long monthStart, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(monthStart);
        return MONTHS[c.get(Calendar.MONTH)] + " " + c.get(Calendar.YEAR);
    }

    /**
     * Raport miesięczny: wpisy, które zaczęły się w danym miesiącu kalendarzowym, pogrupowane
     * w tygodnie robocze (tydzień na przełomie miesięcy jest przycięty do dni tego miesiąca),
     * z sumą każdego tygodnia i sumą miesiąca.
     */
    public static String buildMonth(List<Entry> all, long monthStart, int firstDay, long now, TimeZone tz) {
        long monthEnd = addMonths(monthStart, 1, tz);
        List<Entry> month = WorkMath.inRange(all, monthStart, monthEnd);
        SimpleDateFormat dm = fmt("dd.MM", tz);
        SimpleDateFormat dmy = fmt("dd.MM.yyyy", tz);
        StringBuilder sb = new StringBuilder();
        sb.append("RAPORT MIESIĘCZNY — GODZINY PRACY\n");
        sb.append("Miesiąc: ").append(monthLabel(monthStart, tz)).append(" (")
                .append(dm.format(monthStart)).append(" – ")
                .append(dmy.format(WorkMath.addDays(monthEnd, -1, tz))).append(")\n");
        if (month.isEmpty()) {
            sb.append("\nBrak wpisów w tym miesiącu.\n");
        }
        long ws = WorkMath.weekStart(monthStart, firstDay, tz);
        while (ws < monthEnd) {
            long we = WorkMath.addWeeks(ws, 1, tz);
            List<Entry> part = WorkMath.inRange(month, ws, we);
            if (!part.isEmpty()) {
                long from = Math.max(ws, monthStart);
                long to = WorkMath.addDays(Math.min(we, monthEnd), -1, tz);
                sb.append("\nTydzień ").append(dm.format(from)).append(" – ").append(dm.format(to)).append('\n');
                appendRows(sb, part, now, tz);
                WorkMath.Summary s = WorkMath.summarize(part, now, tz);
                sb.append("          razem tygodnia: ").append(WorkMath.formatHm(s.minutes)).append(" h  ")
                        .append(WorkMath.formatMoney(s.payCents)).append('\n');
            }
            ws = we;
        }
        appendTotals(sb, month, now, tz);
        return sb.toString();
    }

    private static void appendRows(StringBuilder sb, List<Entry> entries, long now, TimeZone tz) {
        SimpleDateFormat day = fmt("dd.MM", tz);
        SimpleDateFormat hm = fmt("HH:mm", tz);
        long lastDay = -1;
        for (Entry e : entries) {
            long d = WorkMath.dayStart(e.start, tz);
            String label = d == lastDay ? "        " : dayShort(e.start, tz) + " " + day.format(e.start);
            lastDay = d;
            long min = WorkMath.minutes(e, now);
            sb.append(label).append("  ")
                    .append(hm.format(e.start)).append("–")
                    .append(e.isRunning() ? "teraz" : hm.format(e.end))
                    .append("  ").append(pad(WorkMath.formatHm(min) + " h", 8))
                    .append("  ").append(pad(WorkMath.formatMoney(WorkMath.payCents(min, e.rateCents)), 9));
            if (e.isRunning()) sb.append("  (w trakcie)");
            String n = notes(e, tz);
            if (!n.isEmpty()) sb.append("  [").append(n).append(']');
            sb.append('\n');
        }
    }

    private static void appendTotals(StringBuilder sb, List<Entry> entries, long now, TimeZone tz) {
        WorkMath.Summary s = WorkMath.summarize(entries, now, tz);
        sb.append("\n");
        sb.append("Dni pracy:   ").append(s.days).append('\n');
        sb.append("Razem:       ").append(WorkMath.formatHm(s.minutes)).append(" h (")
                .append(WorkMath.formatDecimalHours(s.minutes)).append(" h)\n");
        if (!entries.isEmpty()) {
            sb.append(s.mixedRates ? "Śr. stawka:  " : "Stawka:      ")
                    .append(WorkMath.formatMoney(s.averageRateCents)).append("/h")
                    .append(s.mixedRates ? " (różne stawki)\n" : "\n");
        }
        sb.append("DO WYPŁATY:  ").append(WorkMath.formatMoney(s.payCents)).append(" brutto\n");
    }

    static int dayOfWeek(long t, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(t);
        return c.get(Calendar.DAY_OF_WEEK);
    }

    private static String pad(String s, int w) {
        StringBuilder b = new StringBuilder();
        for (int i = s.length(); i < w; i++) b.append(' ');
        return b.append(s).toString();
    }

    static SimpleDateFormat fmt(String p, TimeZone tz) {
        SimpleDateFormat f = new SimpleDateFormat(p, Locale.US);
        f.setTimeZone(tz);
        return f;
    }
}
