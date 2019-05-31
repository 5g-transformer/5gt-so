graph [
  node [
    id 0
    label "vnf2"
    vnf_name "vnf2"
    processing_time 2
    place_at [u'h1']
    requirements [ 
      storage 0.5
      cpu 1
      memory 2
    ]
    cluster 1
  ]
  node [
    id 1
    label "vnf1"
    vnf_name "vnf1"
    processing_time 4
    place_at [u'h1']
    requirements [ 
      storage 10
      cpu 1
      memory 4
    ]
    cluster 1
  ]
  edge [
    source 0
    target 1
    traffic 10
    prob 1.0
  ]
]
