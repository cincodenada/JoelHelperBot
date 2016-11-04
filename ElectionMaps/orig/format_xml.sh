for i in `ls *.html`; do
    if [ `wc -l $i | cut -d\  -f1` -eq 1 ]; then
        tidy -xml -q -w 0 $i > tmp
#       MAPSTART=`grep -n -m1 map | cut -d: -f1`
#       tail -n+$MAPSTART > tmp_tail
#       MAPEND=`grep -n -m1 img`
#       head -n$MAPEND > $i
        mv tmp $i
    fi
done
