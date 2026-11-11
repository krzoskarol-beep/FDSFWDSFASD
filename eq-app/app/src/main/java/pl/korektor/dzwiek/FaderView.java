package pl.korektor.dzwiek;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

/**
 * Pionowy suwak (fader) jak w konsolecie studyjnej: tor, wypełnienie od środka
 * (0 dB), bursztynowa nasadka i kreska środka. Wartość to ułamek 0..1 (dół..góra).
 */
public class FaderView extends View {

    public interface OnFractionChanged {
        void onFractionChanged(FaderView view, float fraction, boolean fromUser);
    }

    private final Paint trackPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint centerPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint knobPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF rect = new RectF();

    private final float dp;
    private float fraction = 0.5f;
    private boolean enabledLook = true;
    private OnFractionChanged listener;

    public FaderView(Context context, AttributeSet attrs) {
        super(context, attrs);
        dp = getResources().getDisplayMetrics().density;
        trackPaint.setColor(context.getColor(R.color.fader_track));
        fillPaint.setColor(context.getColor(R.color.accent));
        centerPaint.setColor(context.getColor(R.color.line));
        knobPaint.setColor(context.getColor(R.color.accent));
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);
    }

    public void setOnFractionChanged(OnFractionChanged l) { listener = l; }

    public void setFraction(float f) {
        fraction = clamp01(f);
        invalidate();
    }

    public float getFraction() { return fraction; }

    public void setEnabledLook(boolean enabled) {
        enabledLook = enabled;
        setAlpha(enabled ? 1f : 0.4f);
        invalidate();
    }

    private float knobHalf() { return 9f * dp; }
    private float usableTop() { return getPaddingTop() + knobHalf(); }
    private float usableBottom() { return getHeight() - getPaddingBottom() - knobHalf(); }

    @Override
    protected void onDraw(Canvas canvas) {
        float cx = getWidth() / 2f;
        float top = usableTop();
        float bottom = usableBottom();
        if (bottom <= top) return;
        float trackW = 5f * dp;

        // Tor
        rect.set(cx - trackW / 2f, top, cx + trackW / 2f, bottom);
        canvas.drawRoundRect(rect, trackW / 2f, trackW / 2f, trackPaint);

        float center = (top + bottom) / 2f;
        float knobY = bottom - fraction * (bottom - top);

        // Wypełnienie od środka (0 dB) do nasadki
        float fillTop = Math.min(center, knobY);
        float fillBottom = Math.max(center, knobY);
        rect.set(cx - trackW / 2f, fillTop, cx + trackW / 2f, fillBottom);
        canvas.drawRoundRect(rect, trackW / 2f, trackW / 2f, fillPaint);

        // Kreska środka (0 dB)
        canvas.drawRect(cx - 9f * dp, center - 0.8f * dp, cx + 9f * dp, center + 0.8f * dp, centerPaint);

        // Nasadka
        float knobW = 26f * dp, knobH = 2f * knobHalf();
        rect.set(cx - knobW / 2f, knobY - knobH / 2f, cx + knobW / 2f, knobY + knobH / 2f);
        canvas.drawRoundRect(rect, 5f * dp, 5f * dp, knobPaint);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (!enabledLook) return false;
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                getParent().requestDisallowInterceptTouchEvent(true);
                // fallthrough
            case MotionEvent.ACTION_MOVE:
                updateFromY(event.getY());
                return true;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                getParent().requestDisallowInterceptTouchEvent(false);
                performClick();
                return true;
        }
        return super.onTouchEvent(event);
    }

    @Override
    public boolean performClick() {
        super.performClick();
        return true;
    }

    private void updateFromY(float y) {
        float top = usableTop();
        float bottom = usableBottom();
        if (bottom <= top) return;
        float f = (bottom - y) / (bottom - top);
        fraction = clamp01(f);
        invalidate();
        if (listener != null) listener.onFractionChanged(this, fraction, true);
    }

    private static float clamp01(float f) {
        if (f < 0f) return 0f;
        if (f > 1f) return 1f;
        return f;
    }
}
