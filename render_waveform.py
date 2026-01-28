import librosa
import numpy as np
from scipy.signal import butter, lfilter
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

def render_waveform(audio, output, bins=100, dpi=60, low_color="#1f71db", mid_color="#b26403", high_color="#f5ead6"):
    # 1. Load Audio
    y, sr = librosa.load(audio, sr=None)
    
    # 2. Filtering Logic (Internalized for thread safety)
    def butter_filter(data, cutoff, fs, btype):
        nyq = 0.5 * fs
        # Handle the list for bandpass or scalar for low/high
        norm = [c / nyq for c in cutoff] if isinstance(cutoff, list) else cutoff / nyq
        b, a = butter(4, norm, btype=btype)
        return lfilter(b, a, data)

    y_low = np.abs(butter_filter(y, 250, sr, 'low'))
    y_mid = np.abs(butter_filter(y, [250, 4000], sr, 'band'))
    y_high = np.abs(butter_filter(y, 4000, sr, 'high'))

    # 3. Binning Logic
    def get_bins(data, bin_count):
        chunks = np.array_split(data, bin_count)
        # Avoid mean of empty slice warning with max(1, ...)
        return np.array([np.mean(chunk) if len(chunk) > 0 else 0 for chunk in chunks])

    b_low = get_bins(y_low, bins)
    b_mid = get_bins(y_mid, bins)
    b_high = get_bins(y_high, bins)

    # 4. Thread-Safe Plotting (Object-Oriented API)
    # We create a Figure directly instead of using plt.figure()
    fig = Figure(figsize=(12, 6), facecolor=(0, 0, 0, 0)) # RGBA: Alpha 0
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(111)

    x = np.arange(bins)

    # Symmetrical Plotting
    ax.bar(x, b_low, bottom=-b_low/2, color=low_color, alpha=0.5, width=0.8)
    ax.bar(x, b_mid, bottom=-b_mid/2, color=mid_color, alpha=0.6, width=0.8)
    ax.bar(x, b_high, bottom=-b_high/2, color=high_color, alpha=0.8, width=0.8)

    # Axis Formatting
    max_val = max(b_high.max(), b_mid.max(), b_low.max())
    ax.set_ylim(-max_val, max_val)
    ax.axis('off')

    # 5. Save with Transparency
    # Note: bbox_inches='tight' can sometimes cause issues with fixed aspect ratios
    # but works well here for removing padding.
    fig.savefig(output, dpi=dpi, bbox_inches='tight', transparent=True)