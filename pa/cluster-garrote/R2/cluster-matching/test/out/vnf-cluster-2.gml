graph [
  node [
    id 0
    label "vnf3"
    vnf_name "vnf3"
    processing_time 0.5
    place_at [u'h2']
    requirements [ 
      storage 1
      cpu 1
      memory 1
    ]
    cluster 2
  ]
  node [
    id 1
    label "vnf4"
    vnf_name "vnf4"
    processing_time 10
    place_at [u'h2']
    requirements [ 
      storage 10
      cpu 4
      memory 8
    ]
    cluster 2
  ]
  node [
    id 2
    label "vnf5"
    vnf_name "vnf5"
    processing_time 0.1
    place_at [u'h2']
    requirements [ 
      storage 0.1
      cpu 1
      memory 0.5
    ]
    cluster 2
  ]
  edge [
    source 0
    target 2
    traffic 6
    prob 1.0
  ]
  edge [
    source 1
    target 2
    traffic 4
    prob 1.0
  ]
]
