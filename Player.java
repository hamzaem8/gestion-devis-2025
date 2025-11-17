
import java.util.ArrayList;
import java.util.List;

public class Player {
    private String mode;
    private List<String> playlist = new ArrayList<>();
    private int currentTrack = 0;

    public Player() {
        this.mode = "Ready";
        for (int i = 1; i <= 12; i++) {
            playlist.add("Track " + i);
        }
    }

    public void changeMode(String mode) {
        this.mode = mode;
    }

    public String getMode() {
        return mode;
    }

    public String startPlayback() {
        return "Playing " + playlist.get(currentTrack);
    }

    public String nextTrack() {
        currentTrack++;
        if (currentTrack > playlist.size() - 1) {
            currentTrack = 0;
        }
        return "Playing " + playlist.get(currentTrack);
    }

    public String previousTrack() {
        currentTrack--;
        if (currentTrack < 0) {
            currentTrack = playlist.size() - 1;
        }
        return "Playing " + playlist.get(currentTrack);
    }

    public void setCurrentTrackAfterStop() {
        this.currentTrack = 0;
    }

	public String onPlay() {
		if(mode.equals("Locked")) {
			changeMode("Ready");
	        return "Ready";
		}
		if(mode.equals("Playing")) {
			changeMode("Ready");
	        return "Paused...";
		}
		if(mode.equals("Ready")) {
	        String action = startPlayback();
	        changeMode("Playing");
	        return action;
		}
		throw new RuntimeException();
	}

	public String onLock() {
		if(mode.equals("Locked")) {
	            return "Locked...";
		}
		if(mode.equals("Playing")) {
			changeMode("Locked");
	        setCurrentTrackAfterStop();
	        return "Stop playing";
		}
		if(mode.equals("Ready")) {
	        changeMode("Locked");
	        return "Locked...";
		}
		throw new RuntimeException();
	}

	public String onNext() {
		if(mode.equals("Playing")) 
			return nextTrack();
		else return "Locked...";
	}

	public String onPrevious() {
		if(mode.equals("Playing")) 
			return previousTrack();
		else return "Locked...";
	}
}
