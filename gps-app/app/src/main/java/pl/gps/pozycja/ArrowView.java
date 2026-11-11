package pl.gps.pozycja;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

/** Okrągła tarcza ze strzałką wskazującą kierunek do samochodu. */
public class ArrowView extends View {

    private final Paint dialPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint arrowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path arrow = new Path();

    private float angle;
    private boolean visible;
    private boolean arrived;

    public ArrowView(Context context, AttributeSet attrs) {
        super(context, attrs);
        dialPaint.setStyle(Paint.Style.FILL);
        dialPaint.setColor(context.getColor(R.color.dial));
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);
        arrowPaint.setStyle(Paint.Style.FILL);
    }

    /** @param degrees obrót strzałki zgodnie z ruchem wskazówek zegara, 0 = do góry ekranu */
    public void setAngle(float degrees) {
        angle = degrees;
        visible = true;
        invalidate();
    }

    public void hideArrow() {
        visible = false;
        invalidate();
    }

    /** Samochód jest tuż obok: zamiast strzałki rysujemy zieloną kropkę. */
    public void setArrived(boolean arrived) {
        if (this.arrived != arrived) {
            this.arrived = arrived;
            invalidate();
        }
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        float cx = w / 2f, cy = h / 2f, r = Math.min(w, h) / 2f;
        arrow.reset();
        arrow.moveTo(cx, cy - r * 0.78f);             // grot
        arrow.lineTo(cx + r * 0.42f, cy + r * 0.55f); // prawy róg
        arrow.lineTo(cx, cy + r * 0.28f);             // wcięcie
        arrow.lineTo(cx - r * 0.42f, cy + r * 0.55f); // lewy róg
        arrow.close();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float cx = getWidth() / 2f, cy = getHeight() / 2f, r = Math.min(getWidth(), getHeight()) / 2f;
        canvas.drawCircle(cx, cy, r, dialPaint);

        if (arrived) {
            arrowPaint.setColor(getContext().getColor(R.color.ok));
            canvas.drawCircle(cx, cy, r * 0.35f, arrowPaint);
            return;
        }
        if (!visible) return;

        arrowPaint.setColor(getContext().getColor(R.color.primary));
        canvas.save();
        canvas.rotate(angle, cx, cy);
        canvas.drawPath(arrow, arrowPaint);
        canvas.restore();
    }
}
