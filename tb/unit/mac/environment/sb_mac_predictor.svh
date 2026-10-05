// Included by sb_mac_pkg.sv; do not compile this header separately.
class sb_mac_predictor extends uvm_subscriber #(sb_mac_item);
  `uvm_component_utils(sb_mac_predictor)
  uvm_analysis_port #(sb_mac_item) expected;
  int unsigned accumulator;
  int unsigned positive_wraps;
  int unsigned negative_wraps;
  bit injected;

  covergroup result_cg with function sample (logic [31:0] value, int wrap_kind);
    option.per_instance = 1;
    result: coverpoint value {
      bins zero = {0};
      bins positive = {[1 : 32'h7fff_ffff]};
      bins negative = {[32'h8000_0000 : 32'hffff_ffff]};
    }
    wrap: coverpoint wrap_kind {bins none = {0}; bins positive = {1}; bins negative = {2};}
  endgroup

  function new(string name, uvm_component parent);
    super.new(name, parent);
    expected  = new("expected", this);
    result_cg = new;
  endfunction

  function void write(sb_mac_item t);
    sb_mac_item prediction;
    longint signed wide;
    int wrap_kind;
    prediction = sb_mac_item::type_id::create("prediction");
    prediction.event_id = t.event_id;
    wide = $signed(accumulator);
    wrap_kind = 0;
    if (t.rst_n && !t.clear && t.enable) begin
      wide += int'(t.a) * int'(t.b);
      if (wide > 64'sd2147483647) begin
        wrap_kind = 1;
        positive_wraps++;
      end else if (wide < -64'sd2147483648) begin
        wrap_kind = 2;
        negative_wraps++;
      end
    end
    accumulator =
      sb_mac_next(accumulator, int'(t.a), int'(t.b), int'(t.rst_n), int'(t.clear), int'(t.enable));
    prediction.value = accumulator;
    result_cg.sample(accumulator, wrap_kind);
    // Corrupt only the checker stream: neither the DUT nor model state is
    // changed. A negative regression must reject this simulation.
    // verilog_lint: waive plusarg-assignment -- Presence-only boolean switch.
    if ($test$plusargs("SB_INJECT_MISMATCH") && !injected) begin
      prediction.value ^= 32'h1;
      injected = 1;
    end
    expected.write(prediction);
  endfunction
endclass
