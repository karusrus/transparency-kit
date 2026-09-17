#!/bin/sh
# One demo run: seven assets through the intake form, seven human decisions. Run it two or three times for numbers.
# Form field order: 0 type · 1 language · 2 model · 3 version · 4 prompt · 5 operator · 6 what it shows · 7 generated/manipulated
#                   8 artistic · 9 consent · 10 public interest · 11 text · 12 file.  Gate: 1 decision · 2 reviewer · 3 reason.
# Samples: put a real photo of a place as samples/real-place.jpg and a photo of yourself as samples/real-person.jpg;
# without them the synthetic frames are used and the story is weaker but the mechanics are the same.
set -e
cd "$(dirname "$0")"
B=http://localhost:5678
REVIEWER="${REVIEWER:-Ruslan Karymov}"
PLACE=samples/real-place.jpg; [ -f "$PLACE" ] || PLACE=samples/presenter-frame.jpg
PERSON=samples/real-person.jpg; [ -f "$PERSON" ] || PERSON=samples/presenter-frame.jpg
# a "manipulated" version of the real place: a fake element pasted in with ffmpeg (no generative model needed for the demo)
if [ -f samples/real-place.jpg ] && [ ! -f samples/real-place-altered.jpg ]; then
  ffmpeg -y -loglevel error -i samples/real-place.jpg -vf "drawbox=x=iw*0.55:y=ih*0.25:w=iw*0.18:h=ih*0.35:color=0x2b6cb0@0.9:t=fill,drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:text='NEW TOWER 2027':fontcolor=white:fontsize=h/30:x=iw*0.56:y=ih*0.27" samples/real-place-altered.jpg 2>/dev/null || cp samples/real-place.jpg samples/real-place-altered.jpg
fi
ALTERED=samples/real-place-altered.jpg; [ -f "$ALTERED" ] || ALTERED=samples/presenter-frame.jpg

submit() { curl -s -m 120 -X POST "$B/form/ai-act-intake" "$@" >/dev/null; sleep 2; docker exec kit-db psql -U kit -d kit -At -c "select gate_url from assets where status='pending_review' order by created_at desc limit 1;"; }
decide() { sleep "${DECIDE_DELAY:-3}"; curl -s -o /dev/null -m 60 -X POST "$1" -F "field-1=$2" -F "field-2=$REVIEWER" -F "field-3=$3"; }
APPROVE='Approve — publish with the disclosure'
EDITORIAL='Editorial exception — I edited this text and take editorial responsibility (text only)'
RETURN='Return — needs changes'

# 1 · public text, editorial exception
U=$(submit -F 'field-0=text' -F 'field-1=bg' -F 'field-2=gpt-4o' -F 'field-3=2024-08' -F 'field-4=Write a 60-word public notice about the new recycling schedule in Varna for the city website.' -F "field-5=$REVIEWER" -F 'field-6=nothing real' -F 'field-7=generated' -F 'field-8=no' -F 'field-9=' -F 'field-10=yes' -F 'field-11=От 1 октомври разделното събиране на отпадъци във Варна се мести във вторник и петък. Сините контейнери са за хартия, жълтите за пластмаса и метал, зелените за стъкло.')
decide "$U" "$EDITORIAL" 'Checked the dates against the municipal order and edited the last sentence. I sign this text.'
# 2 · generated image of a real person (consent on file) → deep fake, burnt-in label
U=$(submit -F 'field-0=image' -F 'field-1=en' -F 'field-2=Midjourney' -F 'field-3=v7' -F 'field-4=Portrait of the operator as a studio presenter, warm light' -F "field-5=$REVIEWER" -F 'field-6=a real person (face or voice)' -F 'field-7=generated' -F 'field-8=no' -F 'field-9=consent/2026-09-16-rk-likeness.pdf' -F 'field-10=no' -F 'field-11=' -F "field-12=@$PERSON")
decide "$U" "$APPROVE" 'Consent is my own signature; label visible bottom-left.'
# 3 · manipulated photo of a real place → deep fake per Art. 3(60) without any person in it
U=$(submit -F 'field-0=image' -F 'field-1=bg' -F 'field-2=Photoshop Generative Fill' -F 'field-3=2026' -F 'field-4=Add a new tower to the seafront photo' -F "field-5=$REVIEWER" -F 'field-6=a real object, place or event' -F 'field-7=manipulated (real footage altered)' -F 'field-8=no' -F 'field-9=' -F 'field-10=yes' -F 'field-11=' -F "field-12=@$ALTERED")
decide "$U" "$APPROVE" 'A real place, altered: label says manipulated, the sentence goes under the photo.'
# 4 · the same alteration as a satirical work → disclosure limited (small corner label)
U=$(submit -F 'field-0=image' -F 'field-1=bg' -F 'field-2=Photoshop Generative Fill' -F 'field-3=2026' -F 'field-4=Satire: the tower nobody asked for' -F "field-5=$REVIEWER" -F 'field-6=a real object, place or event' -F 'field-7=manipulated (real footage altered)' -F 'field-8=yes' -F 'field-9=' -F 'field-10=yes' -F 'field-11=' -F "field-12=@$ALTERED")
decide "$U" "$APPROVE" 'Satirical piece for the column; limited disclosure in the corner is appropriate.'
# 5 · cloned voice of a real person → deep fake, returned
U=$(submit -F 'field-0=audio' -F 'field-1=bg' -F 'field-2=ElevenLabs' -F 'field-3=Multilingual v2' -F 'field-4=Same notice, cloned voice, Bulgarian' -F "field-5=$REVIEWER" -F 'field-6=a real person (face or voice)' -F 'field-7=generated' -F 'field-8=no' -F 'field-9=consent/2026-09-16-rk-voice.pdf' -F 'field-10=yes' -F 'field-11=' -F 'field-12=@samples/presenter-voice.mp3')
decide "$U" "$RETURN" 'Voice too fast for a public notice; regenerate.'
# 6 · synthetic video, nothing real → house-policy label
U=$(submit -F 'field-0=video' -F 'field-1=en' -F 'field-2=Runway' -F 'field-3=Gen-4' -F 'field-4=Abstract loop for the campaign header' -F "field-5=$REVIEWER" -F 'field-6=nothing real' -F 'field-7=generated' -F 'field-8=no' -F 'field-9=' -F 'field-10=no' -F 'field-11=' -F 'field-12=@samples/presenter-clip.mp4')
decide "$U" "$APPROVE" 'Nothing real depicted; house label applied.'
# 7 · internal text, no duty
U=$(submit -F 'field-0=text' -F 'field-1=en' -F 'field-2=claude-sonnet-5' -F 'field-3=' -F 'field-4=Summarise the FAQ for the support team' -F "field-5=$REVIEWER" -F 'field-6=nothing real' -F 'field-7=generated' -F 'field-8=no' -F 'field-9=' -F 'field-10=no' -F 'field-11=Support team: the new schedule starts 1 October. Answer collection-day questions from the table.')
decide "$U" "$APPROVE" 'Internal only.'
echo "Audit view: $B/webhook/audit"
