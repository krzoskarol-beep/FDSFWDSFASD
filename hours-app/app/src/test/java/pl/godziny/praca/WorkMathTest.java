package pl.godziny.praca;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.Calendar;
import java.util.Collections;
import java.util.List;
import java.util.TimeZone;

public class WorkMathTest {

    static final TimeZone WAW = TimeZone.getTimeZone("Europe/Warsaw");
    static final TimeZone NY = TimeZone.getTimeZone("America/New_York");

    static long t(TimeZone tz, int y, int mo, int d, int h, int mi) {
        Calendar c = Calendar.getInstance(tz);
        c.clear();
        c.set(y, mo - 1, d, h, mi, 0);
        return c.getTimeInMillis();
    }

    @Test public void weekStartsOnMondayOrSunday() {
        long wed = t(WAW, 2026, 11, 25, 14, 30);                 // środa
        assertEquals(t(WAW, 2026, 11, 23, 0, 0), WorkMath.weekStart(wed, Calendar.MONDAY, WAW));
        assertEquals(t(WAW, 2026, 11, 22, 0, 0), WorkMath.weekStart(wed, Calendar.SUNDAY, WAW));
        long sun = t(WAW, 2026, 11, 29, 23, 59);
        assertEquals(t(WAW, 2026, 11, 23, 0, 0), WorkMath.weekStart(sun, Calendar.MONDAY, WAW));
        assertEquals(t(WAW, 2026, 11, 29, 0, 0), WorkMath.weekStart(sun, Calendar.SUNDAY, WAW));
    }

    @Test public void addWeeksSurvivesDaylightSavingChange() {
        // 2026-11-01 w USA: koniec czasu letniego, tydzień ma 169 h.
        long w = WorkMath.weekStart(t(NY, 2026, 10, 28, 12, 0), Calendar.MONDAY, NY);
        assertEquals(t(NY, 2026, 11, 2, 0, 0), WorkMath.addWeeks(w, 1, NY));
        assertEquals(t(NY, 2026, 10, 19, 0, 0), WorkMath.addWeeks(w, -1, NY));
    }

    @Test public void payAt34PerHour() {
        assertEquals(3400, WorkMath.payCents(60, 3400));
        assertEquals(28900, WorkMath.payCents(8 * 60 + 30, 3400));   // 8:30 h = $289.00
        assertEquals(57, WorkMath.payCents(1, 3400));               // 56.67 c -> 57
        assertEquals(136000, WorkMath.payCents(40 * 60, 3400));     // 40 h = $1,360.00
        assertEquals(0, WorkMath.payCents(0, 3400));
    }

    @Test public void minutesDropSecondsAndCountRunning() {
        long s = t(WAW, 2026, 11, 23, 8, 0);
        assertEquals(510, WorkMath.minutes(new Entry(1, s, s + 510 * 60_000L + 59_000), 0));
        assertEquals(90, WorkMath.minutes(new Entry(1, s, 0), s + 90 * 60_000L + 5_000));
    }

    @Test public void summaryOfWeek() {
        long mon = t(WAW, 2026, 11, 23, 8, 0);
        List<Entry> week = Arrays.asList(
                new Entry(1, mon, mon + 8 * WorkMath.HOUR),
                new Entry(2, mon + 9 * WorkMath.HOUR, mon + 10 * WorkMath.HOUR + 15 * WorkMath.MINUTE),
                new Entry(3, mon + 24 * WorkMath.HOUR, mon + 32 * WorkMath.HOUR + 30 * WorkMath.MINUTE));
        WorkMath.Summary s = WorkMath.summarize(week, 3400, 0, WAW);
        assertEquals(8 * 60 + 75 + 8 * 60 + 30, s.minutes);       // 17:45
        assertEquals(60350, s.payCents);                            // 17.75 h * 34
        assertEquals(2, s.days);
    }

    @Test public void inRangeFiltersAndSorts() {
        long w = t(WAW, 2026, 11, 23, 0, 0);
        long next = WorkMath.addWeeks(w, 1, WAW);
        List<Entry> all = Arrays.asList(
                new Entry(1, w + 3 * WorkMath.HOUR, w + 4 * WorkMath.HOUR),
                new Entry(2, w - WorkMath.HOUR, w + WorkMath.HOUR),             // poprzedni tydzień
                new Entry(3, w + WorkMath.HOUR, w + 2 * WorkMath.HOUR),
                new Entry(4, next, next + WorkMath.HOUR));                      // następny
        List<Entry> r = WorkMath.inRange(all, w, next);
        assertEquals(2, r.size());
        assertEquals(3, r.get(0).id);
        assertEquals(1, r.get(1).id);
    }

    @Test public void formatting() {
        assertEquals("8:05", WorkMath.formatHm(485));
        assertEquals("0:00", WorkMath.formatHm(0));
        assertEquals("41:30", WorkMath.formatHm(41 * 60 + 30));
        assertEquals("01:02:03", WorkMath.formatHms(3_723_000));
        assertEquals("8.08", WorkMath.formatDecimalHours(485));
        assertEquals("32.25", WorkMath.formatDecimalHours(32 * 60 + 15));
        assertEquals("$1,096.50", WorkMath.formatMoney(109650));
        assertEquals("$0.57", WorkMath.formatMoney(57));
        assertEquals("$34.00", WorkMath.formatMoney(3400));
    }

    @Test public void parseRate() {
        assertEquals(3400, WorkMath.parseRate("34"));
        assertEquals(3450, WorkMath.parseRate("34,5"));
        assertEquals(3450, WorkMath.parseRate("34.50"));
        assertEquals(3405, WorkMath.parseRate(" $34.05 "));
        assertEquals(-1, WorkMath.parseRate(""));
        assertEquals(-1, WorkMath.parseRate("0"));
        assertEquals(-1, WorkMath.parseRate("abc"));
        assertEquals(-1, WorkMath.parseRate("34.555"));
        assertEquals("34", WorkMath.rateForInput(3400));
        assertEquals("34.50", WorkMath.rateForInput(3450));
    }

    @Test public void endAfterHandlesOvernight() {
        long s = t(WAW, 2026, 11, 23, 22, 0);
        assertEquals(t(WAW, 2026, 11, 23, 23, 30), WorkMath.endAfter(s, 23, 30, 0, WAW));
        assertEquals(t(WAW, 2026, 11, 24, 6, 0), WorkMath.endAfter(s, 6, 0, 0, WAW));
        assertEquals(t(WAW, 2026, 11, 24, 22, 0), WorkMath.endAfter(s, 22, 0, 0, WAW));
        assertEquals(t(WAW, 2026, 11, 23, 16, 0), WorkMath.atTime(s, 16, 0, WAW));
    }

    @Test public void validate() {
        long now = t(WAW, 2026, 11, 25, 12, 0);
        long s = t(WAW, 2026, 11, 24, 8, 0);
        List<Entry> none = Collections.emptyList();
        assertNull(WorkMath.validate(none, -1, s, s + 8 * WorkMath.HOUR, now, WAW));
        assertNotNull(WorkMath.validate(none, -1, s, s, now, WAW));                         // zero
        assertNotNull(WorkMath.validate(none, -1, now + WorkMath.HOUR, 0, now, WAW));       // przyszłość
        assertNotNull(WorkMath.validate(none, -1, s, now + WorkMath.HOUR, now, WAW));       // koniec w przyszłości
        assertNotNull(WorkMath.validate(none, -1, s, s + 25 * WorkMath.HOUR, now, WAW));    // > 24 h

        List<Entry> one = Collections.singletonList(new Entry(7, s, s + 8 * WorkMath.HOUR));
        String err = WorkMath.validate(one, -1, s + WorkMath.HOUR, s + 2 * WorkMath.HOUR, now, WAW);
        assertTrue(err, err.startsWith("Nakłada się"));
        assertNull(WorkMath.validate(one, 7, s + WorkMath.HOUR, s + 2 * WorkMath.HOUR, now, WAW)); // sam siebie
        assertNull(WorkMath.validate(one, -1, s + 8 * WorkMath.HOUR, s + 9 * WorkMath.HOUR, now, WAW)); // styk
    }
}
