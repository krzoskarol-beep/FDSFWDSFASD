package pl.godziny.praca;

import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.TimeZone;

/**
 * Próbka do niezależnej weryfikacji: ~12 tygodni losowych (ale powtarzalnych) zmian z różnymi
 * stawkami, przerwami, zmianami przez północ i nadgodzinami. Zapisuje eksport CSV oraz sumy
 * tygodni policzone przez aplikację; skrypt tools/sprawdz_csv.py przelicza CSV po swojemu
 * i porównuje (w CI krok „Niezależne przeliczenie”).
 */
public class VerificationSampleTest {

    @Test public void writeSample() throws Exception {
        TimeZone tz = TimeZone.getTimeZone("America/New_York");   // z przejściem na czas zimowy
        Random rnd = new Random(20261124);
        long w0 = WorkMath.weekStart(WorkMathTest.t(tz, 2026, 9, 7, 12, 0), Calendar.MONDAY, tz);
        long[] rates = {3400, 3400, 3400, 3650, 2875};
        List<Entry> all = new ArrayList<>();
        long id = 1;
        for (int week = 0; week < 12; week++) {
            long ws = WorkMath.addWeeks(w0, week, tz);
            int days = 4 + rnd.nextInt(3);                 // 4–6 dni ⇒ zwykle 32–60 h
            for (int d = 0; d < days; d++) {
                long day = WorkMath.addDays(ws, d, tz);
                int startMin = (rnd.nextBoolean() ? 6 * 60 : 21 * 60) + rnd.nextInt(60); // też nocne
                long s = WorkMath.atTime(day, startMin / 60, startMin % 60, tz) + rnd.nextInt(60) * 1000L;
                long len = (6 * 60 + rnd.nextInt(6 * 60)) * WorkMath.MINUTE + rnd.nextInt(60) * 1000L;
                int brk = new int[]{0, 0, 15, 30, 30, 45}[rnd.nextInt(6)];
                long rate = rates[rnd.nextInt(rates.length)];
                boolean manual = rnd.nextInt(5) == 0;
                all.add(new Entry(id++, s, s + len, brk, rate, s, s + len, manual));
            }
        }

        File dir = new File(System.getProperty("verify.dir", "build/weryfikacja"));
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        try (Writer out = new OutputStreamWriter(new FileOutputStream(new File(dir, "probka.csv")), StandardCharsets.UTF_8)) {
            out.write("﻿" + Csv.export(all, 0, tz));
        }
        SimpleDateFormat iso = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        iso.setTimeZone(tz);
        int overtimeWeeks = 0;
        try (Writer out = new OutputStreamWriter(new FileOutputStream(new File(dir, "oczekiwane.txt")), StandardCharsets.UTF_8)) {
            for (int week = 0; week < 12; week++) {
                long ws = WorkMath.addWeeks(w0, week, tz);
                List<Entry> wk = WorkMath.inRange(all, ws, WorkMath.addWeeks(ws, 1, tz));
                WorkMath.Summary s = WorkMath.summarize(wk, true, 0, tz);
                if (s.overtimeMinutes > 0) overtimeWeeks++;
                out.write(iso.format(ws) + " " + s.minutes + " " + s.payCents + "\n");
            }
        }
        assertTrue("próbka musi zawierać tygodnie z nadgodzinami", overtimeWeeks >= 3);
    }
}
