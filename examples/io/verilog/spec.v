// Benchmark "ham3" written by ABC on Wed Nov  1 10:46:34 2023

module ham3 ( 
    a, b, c,
    x, y, z  );
  input  a, b, c;
  output x, y, z;
  assign x = a ? (~b | (b & ~c)) : (b & c);
  assign y = a ? (~c | (b & c)) : (~b & c);
  assign z = a ? (~b | (b & c)) : (b & ~c);
endmodule


