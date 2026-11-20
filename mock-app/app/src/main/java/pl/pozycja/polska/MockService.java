package pl.pozycja.polska;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import java.util.Random;

/**
 * Usługa pierwszoplanowa: co sekundę wysyła wybraną pozycję w Polsce do podmienionych
 * dostawców lokalizacji, także gdy ekran aplikacji jest zamknięty. Zatrzymanie usuwa
 * dostawców testowych i telefon wraca do prawdziwej pozycji.
 */
public class MockService extends Service {

    public static final String ACTION_STOP = "pl.pozycja.polska.STOP";
    /** Ekran słuchający zmian stanu (ten sam proces, więc wystarczy zwykłe wywołanie). */
    public interface Listener {
        /** @param error komunikat błędu albo {@code null}, gdy to zwykła zmiana stanu */
        void onStateChanged(String error);
    }

    private static Listener listener;

    public static void setListener(Listener l) {
        listener = l;
    }

    private static final String CHANNEL = "pozycja";
    private static final int NOTIF_ID = 1;
    private static final long INTERVAL_MS = 1000;
    private static final double JITTER_M = 3.0;

    /** Stan dla ekranu (jeden proces, więc wystarczy pole statyczne). */
    public static volatile boolean running;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Random rnd = new Random();
    private MockEngine engine;
    private double lat, lon;

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (engine == null) return;
            if (!MockEngine.isAllowed(MockService.this)) {
                fail(getString(R.string.err_not_allowed));
                return;
            }
            double[] p = Coords.jitter(lat, lon, JITTER_M, rnd);
            engine.push(p[0], p[1], 3f + rnd.nextFloat() * 3f);
            handler.postDelayed(this, INTERVAL_MS);
        }
    };

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }
        MockPrefs prefs = new MockPrefs(this);
        lat = prefs.lat();
        lon = prefs.lon();
        startInForeground(prefs.name());

        if (engine == null) {
            engine = new MockEngine(this);
            try {
                engine.start();
            } catch (SecurityException e) {
                fail(getString(R.string.err_not_allowed));
                return START_NOT_STICKY;
            } catch (RuntimeException e) {
                fail(getString(R.string.err_generic, String.valueOf(e.getMessage())));
                return START_NOT_STICKY;
            }
        }
        handler.removeCallbacks(tick);
        handler.post(tick);
        running = true;
        broadcast(null);
        return START_STICKY;
    }

    private void fail(String message) {
        broadcast(message);
        stopSelf();
    }

    private void broadcast(String error) {
        Listener l = listener;
        if (l != null) l.onStateChanged(error);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        running = false;
        handler.removeCallbacks(tick);
        if (engine != null) {
            engine.stop();
            engine = null;
        }
        broadcast(null);
        super.onDestroy();
    }

    private void startInForeground(String placeName) {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW);
            ch.setDescription(getString(R.string.channel_desc));
            ch.setShowBadge(false);
            nm.createNotificationChannel(ch);
        }

        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent openPi = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        Intent stop = new Intent(this, MockService.class).setAction(ACTION_STOP);
        PendingIntent stopPi = PendingIntent.getService(this, 1, stop,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            b = new Notification.Builder(this, CHANNEL);
        } else {
            b = new Notification.Builder(this).setPriority(Notification.PRIORITY_LOW);
        }
        Notification n = b
                .setSmallIcon(R.drawable.ic_stat)
                .setContentTitle(getString(R.string.notif_title, placeName))
                .setContentText(Coords.format(lat, lon))
                .setContentIntent(openPi)
                .setOngoing(true)
                .addAction(0, getString(R.string.notif_stop), stopPi)
                .build();

        // Typ „specialUse” istnieje dopiero od Androida 14; wcześniej uruchamiamy bez typu.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIF_ID, n);
        }
    }

    // ------------------------------------------------------------------ sterowanie z ekranu
    public static void start(Context context) {
        Intent i = new Intent(context, MockService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(i);
        } else {
            context.startService(i);
        }
    }

    public static void stop(Context context) {
        context.stopService(new Intent(context, MockService.class));
    }
}
