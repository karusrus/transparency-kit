#!/bin/sh
# Seeds the kit with four assets and four human decisions, then prints the audit URL.
# Field indexes follow the form order (0 type · 1 language · 2 model · 3 version · 4 prompt · 5 operator · 6 real person · 7 consent · 8 public · 9 text · 10 file);
# the gate's first field is the read-only context block, so decisions start at field-1.
set -e
cd "$(dirname "$0")"
B=http://localhost:5678
submit() { curl -s -X POST "$B/form/ai-act-intake" "$@" | sed -n 's/.*"formWaitingUrl":"\([^"]*\)".*/\1/p'; }
decide() { curl -s -o /dev/null -X POST "$1" -F "field-1=$2" -F 'field-2=Ruslan Karymov' -F "field-3=$3"; }
APPROVE='Approve — publish with the disclosure'
EDITORIAL='Editorial exception — I edited this text and take editorial responsibility (text only)'
RETURN='Return — needs changes'

U=$(submit -F 'field-0=text' -F 'field-1=bg' -F 'field-2=gpt-4o' -F 'field-3=2024-08' \
  -F 'field-4=Write a 60-word public notice about the new recycling schedule in Varna for the city website.' \
  -F 'field-5=Ruslan Karymov' -F 'field-6=no' -F 'field-7=' -F 'field-8=yes' \
  -F 'field-9=От 1 октомври разделното събиране на отпадъци във Варна се мести във вторник и петък. Сините контейнери са за хартия, жълтите за пластмаса и метал, зелените за стъкло. Моля, изнасяйте контейнерите до 7 ч.')
sleep 2; decide "$U" "$EDITORIAL" 'Checked the dates against the municipal order and edited the last sentence. I sign this text.'

U=$(submit -F 'field-0=image' -F 'field-1=en' -F 'field-2=Midjourney' -F 'field-3=v7' \
  -F 'field-4=Portrait of a smiling presenter in a studio, warm light, looking at camera' \
  -F 'field-5=Ruslan Karymov' -F 'field-6=yes' -F 'field-7=consent/2026-09-16-rk-likeness.pdf' -F 'field-8=no' -F 'field-9=' \
  -F 'field-10=@samples/presenter-frame.jpg')
sleep 3; decide "$U" "$APPROVE" 'Consent on file, label visible bottom-left.'

U=$(submit -F 'field-0=video' -F 'field-1=bg' -F 'field-2=HeyGen' -F 'field-3=Avatar IV' \
  -F 'field-4=Presenter reads the recycling notice in Bulgarian, studio, 15 seconds' \
  -F 'field-5=Ruslan Karymov' -F 'field-6=yes' -F 'field-7=consent/2026-09-16-rk-likeness.pdf' -F 'field-8=yes' -F 'field-9=' \
  -F 'field-10=@samples/presenter-clip.mp4')
sleep 6; decide "$U" "$RETURN" 'Lip sync drifts after second 8. Regenerate before publishing.'

U=$(submit -F 'field-0=audio' -F 'field-1=bg' -F 'field-2=ElevenLabs' -F 'field-3=Multilingual v2' \
  -F 'field-4=Same notice, cloned voice, Bulgarian' \
  -F 'field-5=Ruslan Karymov' -F 'field-6=yes' -F 'field-7=consent/2026-09-16-rk-voice.pdf' -F 'field-8=yes' -F 'field-9=' \
  -F 'field-10=@samples/presenter-voice.mp3')
sleep 3; decide "$U" "$APPROVE" 'Voice clone of the operator himself; consent is his own signature. Disclosure goes in the audio description.'
sleep 4
echo "Audit view: $B/webhook/audit"
