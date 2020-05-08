import upco_ale, sys, pathlib


new_ale = upco_ale.Ale()

for f in sys.argv[1:]:
	path = pathlib.Path(f)
	ale = upco_ale.Ale(path)
	for clip in ale.getClips():
		clip = {x: clip.get(x) for x in ["Name","Tape","Start","End","Scene","Take","Camroll","Labroll","Soundroll","Ondiva"]}
		clip.update({"Source": path.stem})
		new_ale.addClips(clip)

new_ale.writeAle("out.ale")