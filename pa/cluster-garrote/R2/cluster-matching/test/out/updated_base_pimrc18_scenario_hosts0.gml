graph [
  node [
    id 0
    label "v_gen_5_4_1526486303.7"
    processing_time 10
    vnf_name "v_gen_5_4_1526486303.7"
    place_at []
    requirements [ 
      storage 18
      cpu 2
      memory 14
    ]
  ]
  node [
    id 1
    label "v_gen_8_1_1526486303.71"
    processing_time 6
    vnf_name "v_gen_8_1_1526486303.71"
    place_at []
    requirements [ 
      storage 80
      cpu 3
      memory 6
    ]
  ]
  node [
    id 2
    label "v_gen_2_1_1526486303.7"
    processing_time 4
    vnf_name "v_gen_2_1_1526486303.7"
    place_at []
    requirements [ 
      storage 93
      cpu 2
      memory 4
    ]
  ]
  node [
    id 3
    label "v_gen_1_9_1526486303.7"
    processing_time 4
    vnf_name "v_gen_1_9_1526486303.7"
    place_at []
    requirements [ 
      storage 12
      cpu 3
      memory 20
    ]
  ]
  node [
    id 4
    label "v_gen_6_19_1526486303.7"
    processing_time 6
    vnf_name "v_gen_6_19_1526486303.7"
    place_at []
    requirements [ 
      storage 3
      cpu 3
      memory 15
    ]
  ]
  node [
    id 5
    label "v_gen_4_15_1526486303.7"
    processing_time 6
    vnf_name "v_gen_4_15_1526486303.7"
    place_at []
    requirements [ 
      storage 64
      cpu 2
      memory 11
    ]
  ]
  node [
    id 6
    label "v_gen_3_13_1526486303.7"
    processing_time 10
    vnf_name "v_gen_3_13_1526486303.7"
    place_at []
    requirements [ 
      storage 34
      cpu 1
      memory 15
    ]
  ]
  node [
    id 7
    label "v_gen_7_18_1526486303.7"
    processing_time 10
    vnf_name "v_gen_7_18_1526486303.7"
    place_at []
    requirements [ 
      storage 19
      cpu 2
      memory 19
    ]
  ]
  edge [
    source 0
    target 4
    delay 7
    traffic 16
    prob 1.0
  ]
  edge [
    source 0
    target 2
    delay 2
    traffic 17
    prob 0.0481454202131
  ]
  edge [
    source 1
    target 7
    delay 10
    traffic 26
    prob 1.0
  ]
  edge [
    source 2
    target 6
    delay 13
    traffic 13
    prob 0.530779119141
  ]
  edge [
    source 2
    target 5
    delay 5
    traffic 17
    prob 0.421075460646
  ]
  edge [
    source 2
    target 3
    delay 14
    traffic 19
    prob 1.0
  ]
  edge [
    source 4
    target 7
    delay 9
    traffic 12
    prob 1.0
  ]
  edge [
    source 4
    target 6
    delay 13
    traffic 22
    prob 1.0
  ]
  edge [
    source 5
    target 7
    delay 6
    traffic 14
    prob 1.0
  ]
]
