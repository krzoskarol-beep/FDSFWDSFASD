package pl.korektor.dzwiek;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;

/**
 * Usługa pierwszoplanowa, która trzyma jeden {@link EqEngine} i utrzymuje efekty
 * podłączone do dźwięku także wtedy, gdy ekran korektora jest zamknięty, a Ty
 * słuchasz w innej aplikacji. Ekran łączy się z usługą (bind), by na żywo zmieniać
 * ustawienia. Wyłączenie korektora zatrzymuje usługę i zwalnia efekty.
 */
public class EqService extends Service {

    public static final String ACTION_STOP = "pl.korektor.dzwiek.STOP";
    private static final String CHANNEL = "korektor";
    private static final int NOTIF_ID = 1;

    public static boolean running;

    private final IBinder binder = new LocalBinder();
    private EqEngine engine;

    public class LocalBinder extends Binder {
        EqService service() { return EqService.this; }
    }

    /** Silnik efektów (tworzony przy pierwszym użyciu). */
    public EqEngine engine() {
        if (engine == null) engine = new EqEngine();
        return engine;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }
        engine(); // utwórz silnik
        applyFromPrefs();
        startInForeground();
        running = true;
        return START_STICKY;
    }

    /** Wczytuje zapamiętane ustawienia i stosuje je do efektów. */
    public void applyFromPrefs() {
        EqEngine e = engine();
        EqPrefs prefs = new EqPrefs(this);
        short preset = prefs.preset();
        short[] levels = prefs.bandLevels();
        if (preset != EqPrefs.PRESET_CUSTOM && preset < e.presetCount()) {
            e.usePreset(preset);
        } else if (levels != null) {
            for (short b = 0; b < e.bandCount() && b < levels.length; b++) {
                e.setBandLevel(b, levels[b]);
            }
        }
        e.setBassStrength(prefs.bass());
        e.setVirtualizerStrength(prefs.virtualizer());
        e.setEnabled(true);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    @Override
    public void onDestroy() {
        running = false;
        if (engine != null) {
            engine.setEnabled(false);
            engine.release();
            engine = null;
        }
        super.onDestroy();
    }

    private void startInForeground() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW);
            ch.setDescription(getString(R.string.channel_desc));
            ch.setShowBadge(false);
            nm.createNotificationChannel(ch);
        }

        Intent open = new Intent(this, EqActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent openPi = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        Intent stop = new Intent(this, EqService.class).setAction(ACTION_STOP);
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
                .setContentTitle(getString(R.string.app_name))
                .setContentText(getString(R.string.notif_active))
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
        Intent i = new Intent(context, EqService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(i);
        } else {
            context.startService(i);
        }
    }

    public static void stop(Context context) {
        context.stopService(new Intent(context, EqService.class));
    }
}
