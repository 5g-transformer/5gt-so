graph [
  node [
    id 0
    label "v_gen_8_18_1526486303.69"
    processing_time 9
    vnf_name "v_gen_8_18_1526486303.69"
    place_at []
    requirements [ 
      storage 100
      cpu 3
      memory 2
    ]
  ]
  node [
    id 1
    label "v_gen_1_5_1526486303.69"
    processing_time 7
    vnf_name "v_gen_1_5_1526486303.69"
    place_at []
    requirements [ 
      storage 77
      cpu 1
      memory 19
    ]
  ]
  node [
    id 2
    label "v_gen_3_15_1526486303.69"
    processing_time 10
    vnf_name "v_gen_3_15_1526486303.69"
    place_at []
    requirements [ 
      storage 45
      cpu 3
      memory 12
    ]
  ]
  node [
    id 3
    label "v_gen_5_12_1526486303.69"
    processing_time 8
    vnf_name "v_gen_5_12_1526486303.69"
    place_at []
    requirements [ 
      storage 8
      cpu 2
      memory 15
    ]
  ]
  node [
    id 4
    label "v_gen_4_3_1526486303.69"
    processing_time 8
    vnf_name "v_gen_4_3_1526486303.69"
    place_at []
    requirements [ 
      storage 19
      cpu 1
      memory 20
    ]
  ]
  node [
    id 5
    label "v_gen_2_10_1526486303.69"
    processing_time 4
    vnf_name "v_gen_2_10_1526486303.69"
    place_at []
    requirements [ 
      storage 91
      cpu 3
      memory 5
    ]
  ]
  node [
    id 6
    label "v_gen_7_15_1526486303.69"
    processing_time 10
    vnf_name "v_gen_7_15_1526486303.69"
    place_at []
    requirements [ 
      storage 89
      cpu 1
      memory 13
    ]
  ]
  node [
    id 7
    label "v_gen_6_20_1526486303.69"
    processing_time 3
    vnf_name "v_gen_6_20_1526486303.69"
    place_at []
    requirements [ 
      storage 30
      cpu 3
      memory 8
    ]
  ]
  edge [
    source 0
    target 6
    delay 14
    traffic 14
    prob 1.0
  ]
  edge [
    source 1
    target 2
    delay 2
    traffic 28
    prob 0.0654896847559
  ]
  edge [
    source 1
    target 4
    delay 11
    traffic 29
    prob 0.133692910367
  ]
  edge [
    source 1
    target 5
    delay 5
    traffic 30
    prob 0.800817404877
  ]
  edge [
    source 2
    target 6
    delay 10
    traffic 27
    prob 1.0
  ]
  edge [
    source 3
    target 7
    delay 3
    traffic 24
    prob 1.0
  ]
  edge [
    source 3
    target 4
    delay 11
    traffic 14
    prob 1.0
  ]
  edge [
    source 5
    target 7
    delay 4
    traffic 22
    prob 1.0
  ]
  edge [
    source 6
    target 7
    delay 12
    traffic 28
    prob 1.0
  ]
]
