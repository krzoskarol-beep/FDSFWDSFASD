package pl.gps.pozycja;

import android.content.Context;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * Dziennik diagnostyczny: co się działo w tle (wykrycie jazdy, start usługi, zapis parkingu…).
 * Przechowywany lokalnie w pliku aplikacji, nigdzie nie jest wysyłany, chyba że użytkownik
 * sam go udostępni z ekranu „Diagnostyka”.
 */
final class EventLog {

    static final int MAX_ENTRIES = 500;
    private static final String FILE = "event_log.txt";
    private static final Object LOCK = new Object();

    private EventLog() { }

    /** Dopisuje wpis z bieżącym czasem. Nigdy nie rzuca wyjątku (dziennik nie może psuć aplikacji). */
    static void log(Context c, String message) {
        String time = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date());
        String line = time + "  " + message.replace('\n', ' ') + "\n";
        synchronized (LOCK) {
            File f = file(c);
            try (FileOutputStream out = new FileOutputStream(f, true)) {
                out.write(line.getBytes(StandardCharsets.UTF_8));
            } catch (IOException ignored) {
                return;
            }
            trimIfNeeded(f);
        }
    }

    /** Wpisy od najnowszego do najstarszego. */
    static List<String> read(Context c) {
        synchronized (LOCK) {
            List<String> lines = readLines(file(c));
            List<String> reversed = new ArrayList<>(lines.size());
            for (int i = lines.size() - 1; i >= 0; i--) reversed.add(lines.get(i));
            return reversed;
        }
    }

    static void clear(Context c) {
        synchronized (LOCK) {
            //noinspection ResultOfMethodCallIgnored
            file(c).delete();
        }
    }

    private static File file(Context c) {
        return new File(c.getApplicationContext().getFilesDir(), FILE);
    }

    private static List<String> readLines(File f) {
        if (!f.exists()) return new ArrayList<>();
        List<String> lines = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) lines.add(line);
        } catch (IOException e) {
            // zwracamy to, co udało się przeczytać
        }
        return lines;
    }

    /** Plik rośnie do 1,5× limitu, potem zostaje przycięty do limitu (rzadkie przepisywanie). */
    private static void trimIfNeeded(File f) {
        if (f.length() < MAX_ENTRIES * 120L) return; // szybki test bez czytania pliku
        List<String> lines = readLines(f);
        if (lines.size() <= MAX_ENTRIES * 3 / 2) return;
        List<String> keep = lines.subList(lines.size() - MAX_ENTRIES, lines.size());
        StringBuilder sb = new StringBuilder();
        for (String l : keep) sb.append(l).append('\n');
        try (FileOutputStream out = new FileOutputStream(f, false)) {
            out.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        } catch (IOException ignored) {
            // przy następnym wpisie spróbujemy ponownie
        }
    }
}
