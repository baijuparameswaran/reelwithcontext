from inspect import signature
from reelctxt.media.compose import create_video

def test_create_video_signature():
    sig = signature(create_video)
    params = list(sig.parameters.keys())
    assert params[:3] == ['segments', 'audio_paths', 'output_path']
    for needed in ['music_path','music_volume','duck','captions','caption_mode','caption_max_chars','caption_color','caption_box','caption_box_color','caption_font','ken_burns','ken_burns_zoom']:
        assert needed in params
