package pl.godziny.praca;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

/** Tekst raportu tygodniowego (do podglądu, kopiowania i udostępnienia). */
public final class Report {

    static final String[] DAYS = {"", "Nd", "Pn", "Wt", "Śr", "Cz", "Pt", "Sb"};

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

    public static String build(List<Entry> week, long weekStart, long rateCents, long now, TimeZone tz) {
        SimpleDateFormat day = fmt("dd.MM", tz);
        SimpleDateFormat hm = fmt("HH:mm", tz);
        StringBuilder sb = new StringBuilder();
        sb.append("RAPORT TYGODNIOWY — GODZINY PRACY\n");
        sb.append("Tydzień: ").append(weekLabel(weekStart, tz)).append('\n');
        sb.append("Stawka: ").append(WorkMath.formatMoney(rateCents)).append("/h\n\n");

        if (week.isEmpty()) {
            sb.append("Brak wpisów w tym tygodniu.\n");
        }
        long lastDay = -1;
        for (Entry e : week) {
            long d = WorkMath.dayStart(e.start, tz);
            String label = d == lastDay ? "        " : dayShort(e.start, tz) + " " + day.format(e.start);
            lastDay = d;
            long min = WorkMath.minutes(e, now);
            sb.append(label).append("  ")
                    .append(hm.format(e.start)).append("–")
                    .append(e.isRunning() ? "teraz" : hm.format(e.end))
                    .append("  ").append(pad(WorkMath.formatHm(min) + " h", 8))
                    .append("  ").append(pad(WorkMath.formatMoney(WorkMath.payCents(min, rateCents)), 9));
            if (e.isRunning()) sb.append("  (w trakcie)");
            sb.append('\n');
        }

        WorkMath.Summary s = WorkMath.summarize(week, rateCents, now, tz);
        sb.append("\n");
        sb.append("Dni pracy:   ").append(s.days).append('\n');
        sb.append("Razem:       ").append(WorkMath.formatHm(s.minutes)).append(" h (")
                .append(WorkMath.formatDecimalHours(s.minutes)).append(" h)\n");
        sb.append("Do wypłaty:  ").append(WorkMath.formatMoney(s.payCents)).append('\n');
        return sb.toString();
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
