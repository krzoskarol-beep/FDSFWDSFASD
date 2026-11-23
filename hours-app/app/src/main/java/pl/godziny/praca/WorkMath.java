package pl.godziny.praca;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Obliczenia bez zależności od Androida: granice tygodnia, czas, wypłata, walidacja.
 *
 * Czas wpisu liczony jest w pełnych minutach (sekundy się ucina), a wypłata tygodnia
 * z sumy minut — dzięki temu godziny i kwota w raporcie zawsze do siebie pasują.
 * Wpis należy do dnia i tygodnia, w którym się zaczął (zmiana nocna nie jest dzielona).
 */
public final class WorkMath {

    public static final long MINUTE = 60_000L;
    public static final long HOUR = 60 * MINUTE;
    public static final long MAX_ENTRY = 24 * HOUR;

    private WorkMath() {}

    // ------------------------------------------------------------ tydzień

    /** Północ pierwszego dnia tygodnia zawierającego {@code t}. firstDay: Calendar.MONDAY / SUNDAY. */
    public static long weekStart(long t, int firstDay, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(t);
        startOfDay(c);
        int diff = (c.get(Calendar.DAY_OF_WEEK) - firstDay + 7) % 7;
        c.add(Calendar.DAY_OF_MONTH, -diff);
        return c.getTimeInMillis();
    }

    /** Przesuwa początek tygodnia o {@code weeks} (zmiana czasu letni/zimowy jest uwzględniona). */
    public static long addWeeks(long weekStart, int weeks, TimeZone tz) {
        return addDays(weekStart, 7 * weeks, tz);
    }

    public static long addDays(long t, int days, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(t);
        c.add(Calendar.DAY_OF_MONTH, days);
        return c.getTimeInMillis();
    }

    public static long dayStart(long t, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(t);
        startOfDay(c);
        return c.getTimeInMillis();
    }

    /** Dzień zawierający {@code t}, godzina h:m:00. */
    public static long atTime(long t, int hour, int minute, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(t);
        startOfDay(c);
        c.set(Calendar.HOUR_OF_DAY, hour);
        c.set(Calendar.MINUTE, minute);
        return c.getTimeInMillis();
    }

    private static void startOfDay(Calendar c) {
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
    }

    /** Wpisy zaczynające się w [from, to), posortowane od najstarszego. */
    public static List<Entry> inRange(List<Entry> all, long from, long to) {
        List<Entry> out = new ArrayList<>();
        for (Entry e : all) if (e.start >= from && e.start < to) out.add(e);
        Collections.sort(out, (a, b) -> Long.compare(a.start, b.start));
        return out;
    }

    public static Entry running(List<Entry> all) {
        for (Entry e : all) if (e.isRunning()) return e;
        return null;
    }

    // ------------------------------------------------------------ czas i pieniądze

    public static long minutes(Entry e, long now) {
        return Math.max(0, e.endOr(now) - e.start) / MINUTE;
    }

    /** Wypłata za podane minuty, w centach, zaokrąglona do najbliższego centa. */
    public static long payCents(long minutes, long rateCents) {
        return (minutes * rateCents + 30) / 60;
    }

    public static final class Summary {
        public final long minutes;
        public final long payCents;
        public final int days;

        Summary(long minutes, long payCents, int days) {
            this.minutes = minutes;
            this.payCents = payCents;
            this.days = days;
        }
    }

    public static Summary summarize(List<Entry> week, long rateCents, long now, TimeZone tz) {
        long total = 0;
        java.util.Set<Long> days = new java.util.HashSet<>();
        for (Entry e : week) {
            total += minutes(e, now);
            days.add(dayStart(e.start, tz));
        }
        return new Summary(total, payCents(total, rateCents), days.size());
    }

    /** "8:05" */
    public static String formatHm(long minutes) {
        return String.format(Locale.US, "%d:%02d", minutes / 60, minutes % 60);
    }

    /** "08:05:09" — licznik trwającej zmiany. */
    public static String formatHms(long ms) {
        long s = Math.max(0, ms) / 1000;
        return String.format(Locale.US, "%02d:%02d:%02d", s / 3600, (s / 60) % 60, s % 60);
    }

    /** "8.08" — godziny dziesiętnie (do list płac). */
    public static String formatDecimalHours(long minutes) {
        long hundredths = (minutes * 100 + 30) / 60;
        return String.format(Locale.US, "%d.%02d", hundredths / 100, hundredths % 100);
    }

    /** "$1,096.50" */
    public static String formatMoney(long cents) {
        String sign = cents < 0 ? "-" : "";
        long c = Math.abs(cents);
        return sign + "$" + String.format(Locale.US, "%,d.%02d", c / 100, c % 100);
    }

    /** Stawka wpisana przez użytkownika ("34", "34.5", "34,50") w centach; -1 gdy błędna. */
    public static long parseRate(String text) {
        if (text == null) return -1;
        String t = text.trim().replace(',', '.').replace("$", "");
        if (!t.matches("\\d{1,5}(\\.\\d{0,2})?")) return -1;
        String[] p = t.split("\\.", -1);
        long dollars = Long.parseLong(p[0]);
        long cents = 0;
        if (p.length == 2 && !p[1].isEmpty()) {
            cents = Long.parseLong(p[1].length() == 1 ? p[1] + "0" : p[1]);
        }
        long v = dollars * 100 + cents;
        return v > 0 ? v : -1;
    }

    /** "34" lub "34.50" — do pola edycji stawki. */
    public static String rateForInput(long cents) {
        return cents % 100 == 0 ? String.valueOf(cents / 100)
                : String.format(Locale.US, "%d.%02d", cents / 100, cents % 100);
    }

    // ------------------------------------------------------------ edycja wpisu

    /**
     * Koniec zmiany o godzinie h:m:s liczony względem początku: tego samego dnia, a gdy
     * wypada przed (albo równo z) początkiem — następnego dnia (zmiana przez północ).
     */
    public static long endAfter(long start, int hour, int minute, int second, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz, Locale.US);
        c.setTimeInMillis(start);
        c.set(Calendar.HOUR_OF_DAY, hour);
        c.set(Calendar.MINUTE, minute);
        c.set(Calendar.SECOND, second);
        c.set(Calendar.MILLISECOND, 0);
        if (c.getTimeInMillis() <= start) c.add(Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }

    /**
     * Sprawdza wpis przed zapisem. Zwraca opis błędu albo null, gdy wpis jest poprawny.
     * {@code end == 0} to zmiana w trakcie. {@code selfId} — id edytowanego wpisu (pomijany
     * przy sprawdzaniu nakładania), -1 dla nowego.
     */
    public static String validate(List<Entry> all, long selfId, long start, long end, long now, TimeZone tz) {
        if (start > now) return "Początek nie może być w przyszłości.";
        long realEnd = end == 0 ? now : end;
        if (end != 0 && end <= start) return "Koniec musi być po początku.";
        if (end != 0 && end > now + MINUTE) return "Koniec nie może być w przyszłości.";
        if (realEnd - start > MAX_ENTRY) return "Wpis nie może być dłuższy niż 24 godziny.";
        for (Entry o : all) {
            if (o.id == selfId) continue;
            long oEnd = o.endOr(now);
            if (start < oEnd && o.start < realEnd) {
                java.text.SimpleDateFormat f = new java.text.SimpleDateFormat("dd.MM HH:mm", Locale.US);
                f.setTimeZone(tz);
                return "Nakłada się na inny wpis: " + f.format(o.start) + " – "
                        + (o.isRunning() ? "teraz" : f.format(oEnd)) + ".";
            }
        }
        return null;
    }
}
