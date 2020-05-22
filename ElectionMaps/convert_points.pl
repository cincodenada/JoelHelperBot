use Math::Round;
if(/^m/i) {
  s/^m //i;
  s/ z$//i;
  @pairs = map { my @arr = split ','; \@arr } split ' ';
  @base = @{shift @pairs};
  @out = ([$base[0], $base[1]]);
  for $pair (@pairs) {
    $base[0] += @{$pair}[0];
    $base[1] += @{$pair}[1];
    push(@out, [$base[0], $base[1]]);
  }
  print "      points: " . join(" ", map { map  { round($_) } @{$_} } @out);
  print "\n";
}
else { print }
