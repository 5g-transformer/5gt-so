graph [
  node [
    id 0
    label 1
    disk 8
    cpu 3
    memory 10
  ]
  node [
    id 1
    label 2
    disk 4
    cpu 1
    memory 7
  ]
  node [
    id 2
    label 3
    disk 2
    cpu 2
    memory 10
  ]
  node [
    id 3
    label 4
    disk 5
    cpu 3
    memory 15
  ]
  node [
    id 4
    label 5
    disk 1
    cpu 3
    memory 13
  ]
  node [
    id 5
    label 6
    disk 8
    cpu 1
    memory 4
  ]
  node [
    id 6
    label "start"
  ]
  edge [
    source 0
    target 6
    delay 29
    bw 198
  ]
  edge [
    source 0
    target 1
    delay 25
    bw 196
  ]
  edge [
    source 0
    target 2
    delay 31
    bw 107
  ]
  edge [
    source 1
    target 3
    delay 32
    bw 84
  ]
  edge [
    source 2
    target 4
    delay 29
    bw 167
  ]
  edge [
    source 3
    target 4
    delay 25
    bw 188
  ]
  edge [
    source 4
    target 5
    delay 31
    bw 129
  ]
]