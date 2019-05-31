graph [
  node [
    id 0
    label "v_gen_8_11_1526486303.68"
    processing_time 4
    vnf_name "v_gen_8_11_1526486303.68"
    place_at []
    requirements [ 
      storage 6
      cpu 3
      memory 20
    ]
  ]
  node [
    id 1
    label "v_gen_6_8_1526486303.68"
    processing_time 8
    vnf_name "v_gen_6_8_1526486303.68"
    place_at []
    requirements [ 
      storage 38
      cpu 3
      memory 17
    ]
  ]
  node [
    id 2
    label "v_gen_3_4_1526486303.68"
    processing_time 8
    vnf_name "v_gen_3_4_1526486303.68"
    place_at []
    requirements [ 
      storage 77
      cpu 2
      memory 19
    ]
  ]
  node [
    id 3
    label "v_gen_2_16_1526486303.68"
    processing_time 6
    vnf_name "v_gen_2_16_1526486303.68"
    place_at []
    requirements [ 
      storage 67
      cpu 1
      memory 19
    ]
  ]
  node [
    id 4
    label "v_gen_1_16_1526486303.68"
    processing_time 10
    vnf_name "v_gen_1_16_1526486303.68"
    place_at []
    requirements [ 
      storage 90
      cpu 3
      memory 11
    ]
  ]
  node [
    id 5
    label "v_gen_7_16_1526486303.68"
    processing_time 6
    vnf_name "v_gen_7_16_1526486303.68"
    place_at []
    requirements [ 
      storage 43
      cpu 3
      memory 6
    ]
  ]
  node [
    id 6
    label "v_gen_5_5_1526486303.68"
    processing_time 6
    vnf_name "v_gen_5_5_1526486303.68"
    place_at []
    requirements [ 
      storage 90
      cpu 1
      memory 17
    ]
  ]
  node [
    id 7
    label "v_gen_4_3_1526486303.68"
    processing_time 9
    vnf_name "v_gen_4_3_1526486303.68"
    place_at []
    requirements [ 
      storage 75
      cpu 3
      memory 11
    ]
  ]
  edge [
    source 0
    target 2
    delay 9
    traffic 19
    prob 1.0
  ]
  edge [
    source 0
    target 3
    delay 9
    traffic 29
    prob 1.0
  ]
  edge [
    source 0
    target 5
    delay 13
    traffic 17
    prob 1.0
  ]
  edge [
    source 0
    target 6
    delay 3
    traffic 13
    prob 1.0
  ]
  edge [
    source 1
    target 7
    delay 14
    traffic 20
    prob 0.255958904426
  ]
  edge [
    source 1
    target 5
    delay 3
    traffic 20
    prob 1.0
  ]
  edge [
    source 2
    target 4
    delay 3
    traffic 15
    prob 0.0227978239279
  ]
  edge [
    source 3
    target 4
    delay 4
    traffic 16
    prob 0.878941617191
  ]
  edge [
    source 4
    target 7
    delay 2
    traffic 16
    prob 0.098260558881
  ]
  edge [
    source 6
    target 7
    delay 5
    traffic 17
    prob 0.744041095574
  ]
]
