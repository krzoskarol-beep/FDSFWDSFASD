package pl.gps.pozycja;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

/** Kanały i treść powiadomień aplikacji. */
final class Notifications {

    static final String CHANNEL_DRIVING = "driving";
    static final String CHANNEL_PARKING = "parking";

    static final int ID_DRIVING = 1;
    static final int ID_PARKED = 2;
    static final int ID_BLOCKED = 3;

    private static final String PREFS = "notifications";
    private static final String K_LAST_BLOCKED = "lastBlockedAlert";

    private Notifications() { }

    static void createChannels(Context c) {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        NotificationChannel driving = new NotificationChannel(CHANNEL_DRIVING,
                c.getString(R.string.channel_driving), NotificationManager.IMPORTANCE_LOW);
        driving.setDescription(c.getString(R.string.channel_driving_desc));
        NotificationChannel parking = new NotificationChannel(CHANNEL_PARKING,
                c.getString(R.string.channel_parking), NotificationManager.IMPORTANCE_DEFAULT);
        parking.setDescription(c.getString(R.string.channel_parking_desc));
        nm.createNotificationChannel(driving);
        nm.createNotificationChannel(parking);
    }

    @SuppressWarnings("deprecation")
    private static Notification.Builder builder(Context c, String channel) {
        createChannels(c);
        return Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(c, channel)
                : new Notification.Builder(c);
    }

    private static PendingIntent openApp(Context c, String action, int requestCode) {
        Intent i = new Intent(c, MainActivity.class)
                .setAction(action)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return PendingIntent.getActivity(c, requestCode, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    /** Stałe powiadomienie w trakcie jazdy (wymagane dla usługi działającej w tle). */
    @SuppressWarnings("deprecation")
    static Notification driving(Context c, String text) {
        Intent cancel = new Intent(c, DrivingService.class).setAction(DrivingService.ACTION_CANCEL);
        PendingIntent cancelPi = PendingIntent.getService(c, 10, cancel,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return builder(c, CHANNEL_DRIVING)
                .setSmallIcon(R.drawable.ic_stat_car)
                .setContentTitle(c.getString(R.string.notif_driving_title))
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(openApp(c, Intent.ACTION_MAIN, 11))
                .addAction(new Notification.Action.Builder(null,
                        c.getString(R.string.notif_driving_cancel), cancelPi).build())
                .build();
    }

    static void showParked(Context c, String text) {
        showParked(c, text, false);
    }

    /** @param silent true przy odświeżeniu treści (np. dopisaniu adresu), bez ponownego dźwięku */
    static void showParked(Context c, String text, boolean silent) {
        if (!canPost(c)) return;
        Notification n = builder(c, CHANNEL_PARKING)
                .setSmallIcon(R.drawable.ic_stat_car)
                .setContentTitle(c.getString(R.string.notif_parked_title))
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setAutoCancel(true)
                .setOnlyAlertOnce(silent)
                .setContentIntent(openApp(c, Intent.ACTION_MAIN, 20))
                .addAction(new Notification.Action.Builder(null,
                        c.getString(R.string.parking_navigate),
                        openApp(c, MainActivity.ACTION_NAVIGATE_TO_CAR, 21)).build())
                .build();
        c.getSystemService(NotificationManager.class).notify(ID_PARKED, n);
    }

    /**
     * Android nie pozwolił uruchomić śledzenia jazdy w tle. Najczęstsza przyczyna to optymalizacja
     * baterii, więc dotknięcie otwiera aplikację. Najwyżej raz na dobę, żeby nie męczyć.
     */
    static void showTrackingBlocked(Context c) {
        android.content.SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        long now = System.currentTimeMillis();
        if (!canPost(c) || !DrivePolicy.shouldAlertBlocked(p.getLong(K_LAST_BLOCKED, 0), now)) return;
        p.edit().putLong(K_LAST_BLOCKED, now).apply();
        String text = c.getString(R.string.notif_blocked_text);
        Notification n = builder(c, CHANNEL_PARKING)
                .setSmallIcon(R.drawable.ic_stat_car)
                .setContentTitle(c.getString(R.string.notif_blocked_title))
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setAutoCancel(true)
                .setContentIntent(openApp(c, Intent.ACTION_MAIN, 30))
                .build();
        c.getSystemService(NotificationManager.class).notify(ID_BLOCKED, n);
    }

    static boolean canPost(Context c) {
        return Build.VERSION.SDK_INT < 33
                || c.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
    }
}
