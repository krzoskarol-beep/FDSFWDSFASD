package pl.godziny.praca;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.robolectric.Shadows.shadowOf;

import android.app.AlertDialog;
import android.content.Context;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;

import androidx.test.core.app.ApplicationProvider;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;

import java.util.Calendar;
import java.util.TimeZone;

/** Edycja wpisu przez prawdziwe okno: odejmowanie czasu od zakończonej i trwającej zmiany. */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34)
public class EditEntryTest {

    private static final long H = WorkMath.HOUR, M = WorkMath.MINUTE;
    private EntryStore store;

    @Before public void setUp() {
        Context ctx = ApplicationProvider.getApplicationContext();
        ctx.getSharedPreferences(EntryStore.PREFS, Context.MODE_PRIVATE).edit().clear().commit();
        store = new EntryStore(ctx);
    }

    /** Otwiera okno edycji pierwszego wpisu (w razie potrzeby w poprzednim tygodniu). */
    private AlertDialog openEditor(long entryStart) {
        MainActivity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        long week = WorkMath.weekStart(System.currentTimeMillis(), Calendar.MONDAY, TimeZone.getDefault());
        if (entryStart < week) a.findViewById(R.id.prevWeek).performClick();
        ViewGroup list = a.findViewById(R.id.entryList);
        list.getChildAt(1).performClick();          // 0 = nagłówek dnia, 1 = wpis
        shadowOf(Looper.getMainLooper()).idle();    // pokazanie okna (podpięcie przycisku Zapisz)
        AlertDialog dlg = (AlertDialog) ShadowAlertDialog.getLatestAlertDialog();
        assertTrue(dlg.isShowing());
        return dlg;
    }

    private static void click(AlertDialog dlg, int id) {
        View v = dlg.findViewById(id);
        assertTrue(v.isEnabled());
        v.performClick();
    }

    @Test public void subtractFromFinishedShift() {
        long now = System.currentTimeMillis();
        long s = now - now % M - 5 * H;
        store.add(s, s + 4 * H);

        AlertDialog dlg = openEditor(s);
        click(dlg, R.id.minus15);
        click(dlg, R.id.minus15);
        dlg.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
        shadowOf(Looper.getMainLooper()).idle();

        Entry e = store.all().get(0);
        assertEquals(s, e.start);
        assertEquals(3 * 60 + 30, WorkMath.minutes(e, 0));    // 4:00 − 0:30
    }

    @Test public void subtractFromRunningShiftMovesStart() {
        long now = System.currentTimeMillis();
        long s = now - 3 * H;
        store.add(s, 0);

        AlertDialog dlg = openEditor(s);
        click(dlg, R.id.endBtn);                    // koniec trwającej zmiany da się ustawić
        dlg = openEditor(s);                        // (zegar to osobne okno; wróć do edycji)
        click(dlg, R.id.minus60);
        dlg.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
        shadowOf(Looper.getMainLooper()).idle();

        Entry e = store.all().get(0);
        assertTrue(e.isRunning());
        assertEquals(s + H, e.start);
    }

    @Test public void cannotSubtractMoreThanTheShift() {
        long now = System.currentTimeMillis();
        long s = now - now % M - 2 * H;
        store.add(s, s + 30 * M);

        AlertDialog dlg = openEditor(s);
        click(dlg, R.id.minus60);
        assertEquals(View.VISIBLE, dlg.findViewById(R.id.error).getVisibility());
        dlg.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
        assertEquals(30, WorkMath.minutes(store.all().get(0), 0));   // bez zmian
    }
}
