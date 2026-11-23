package pl.godziny.praca;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class EntryAndReportTest {

    @Test public void codecRoundTripAndSkipsGarbage() {
        List<Entry> in = Arrays.asList(new Entry(1, 1000, 5000), new Entry(2, 6000, 0));
        List<Entry> out = Entry.decode(Entry.encode(in) + "zepsute\n3,9,1\n4,x,5\n");
        assertEquals(2, out.size());
        assertEquals(2, out.get(1).id);
        assertTrue(out.get(1).isRunning());
        assertEquals(5000, out.get(0).end);
        assertEquals(0, Entry.decode(null).size());
    }

    @Test public void weeklyReport() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        long h = WorkMath.HOUR;
        List<Entry> week = Arrays.asList(
                new Entry(1, w + 8 * h, w + 16 * h + 30 * WorkMath.MINUTE),     // Pn 8:30
                new Entry(2, w + 17 * h, w + 18 * h),                           // Pn 1:00
                new Entry(3, w + 24 * h + 22 * h, w + 48 * h + 6 * h));         // Wt 22–06 (przez północ)
        String r = Report.build(week, w, 3400, 0, WorkMathTest.WAW);
        assertTrue(r, r.contains("Tydzień: 23.11 – 29.11.2026"));
        assertTrue(r, r.contains("Stawka: $34.00/h"));
        assertTrue(r, r.contains("Pn 23.11  08:00–16:30    8:30 h    $289.00"));
        assertTrue(r, r.contains("          17:00–18:00    1:00 h     $34.00"));
        assertTrue(r, r.contains("Wt 24.11  22:00–06:00    8:00 h    $272.00"));
        assertTrue(r, r.contains("Dni pracy:   2"));
        assertTrue(r, r.contains("Razem:       17:30 h (17.50 h)"));
        assertTrue(r, r.contains("Do wypłaty:  $595.00"));
    }

    @Test public void reportMarksRunningShiftAndEmptyWeek() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        String r = Report.build(Collections.singletonList(new Entry(1, w + 8 * WorkMath.HOUR, 0)),
                w, 3400, w + 10 * WorkMath.HOUR, WorkMathTest.WAW);
        assertTrue(r, r.contains("08:00–teraz    2:00 h     $68.00  (w trakcie)"));
        assertTrue(Report.build(Collections.emptyList(), w, 3400, 0, WorkMathTest.WAW)
                .contains("Brak wpisów"));
    }
}
