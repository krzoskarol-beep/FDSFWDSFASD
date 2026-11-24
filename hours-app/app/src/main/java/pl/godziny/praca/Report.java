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

    public static String build(List<Entry> week, long weekStart, boolean overtime, long now, TimeZone tz) {
        SimpleDateFormat day = fmt("dd.MM", tz);
        SimpleDateFormat hm = fmt("HH:mm", tz);
        StringBuilder sb = new StringBuilder();
        sb.append("RAPORT TYGODNIOWY — GODZINY PRACY\n");
        sb.append("Tydzień: ").append(weekLabel(weekStart, tz)).append('\n');
        sb.append("Początek tygodnia: ").append(DAYS_FULL[dayOfWeek(weekStart, tz)]).append(", 00:00\n\n");

        if (week.isEmpty()) {
            sb.append("Brak wpisów w tym tygodniu.\n");
        }
        long lastDay = -1;
        boolean anyEdited = false;
        for (Entry e : week) {
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
            if (e.isEdited()) anyEdited = true;
            sb.append('\n');
        }

        WorkMath.Summary s = WorkMath.summarize(week, overtime, now, tz);
        sb.append("\n");
        sb.append("Dni pracy:        ").append(s.days).append('\n');
        sb.append("Razem:            ").append(WorkMath.formatHm(s.minutes)).append(" h (")
                .append(WorkMath.formatDecimalHours(s.minutes)).append(" h)\n");
        if (s.overtimeMinutes > 0) {
            sb.append("  zwykłe:         ").append(WorkMath.formatHm(s.regularMinutes)).append(" h\n");
            sb.append("  nadgodziny:     ").append(WorkMath.formatHm(s.overtimeMinutes)).append(" h (ponad 40 h, ×1.5)\n");
        }
        sb.append("Stawka regularna: ").append(WorkMath.formatMoney(s.regularRateCents)).append("/h\n");
        sb.append("Podstawa:         ").append(WorkMath.formatMoney(s.straightCents)).append('\n');
        if (s.overtimeMinutes > 0) {
            sb.append("Dopłata za nadg.: ").append(WorkMath.formatMoney(s.overtimePremiumCents))
                    .append(" (½ × ").append(WorkMath.formatMoney(s.regularRateCents)).append(" × ")
                    .append(WorkMath.formatDecimalHours(s.overtimeMinutes)).append(" h)\n");
        }
        sb.append("DO WYPŁATY:       ").append(WorkMath.formatMoney(s.payCents)).append(" brutto\n");
        sb.append('\n');
        sb.append(overtime ? "Nadgodziny wg FLSA: ponad 40 h w tygodniu, ×1.5 stawki regularnej.\n"
                : "Nadgodziny nie są liczone (wyłączone w ustawieniach).\n");
        sb.append("Czas liczony co do minuty, bez zaokrąglania. Przerwy odjęte.\n");
        if (anyEdited) sb.append("Wpisy poprawione ręcznie są oznaczone wraz z godzinami z zegara.\n");
        return sb.toString();
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
