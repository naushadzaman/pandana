import _pyaccess
from string import split
import numpy
import numpy as np
import time, copy
    
class PyAccess():
    AGG_SUM = 0
    AGG_AVE = 1
    AGG_STDDEV = 5
    DECAY_EXP = 0
    DECAY_LINEAR = 1
    DECAY_FLAT = 2


    # this function merges the two networks - the first argument is presumed to be the base local street network 
    # while the second argument is a regional network that provides "shortcuts" - canonical example is transit
    # the third agument is the index of the already created walk network
    # the fourth argument is multiplier of edgeweights in the base network (to match units)
    def mergenetworks(my,basenet,addnet,indexofbase=0,multiplier=1.0):
        basenet = copy.deepcopy(basenet)
        NUMNODES = basenet['nodes'].shape[0]
        basenet['edgeweights'] *= multiplier
        # find nearest street node to every transit node
        baseids = my.XYtoNode(addnet['nodes'],gno=indexofbase,distance=-1) 
        assert numpy.intersect1d(basenet['nodeids'],addnet['nodeids']).size == 0
        basenet['nodeids'] = numpy.concatenate((basenet['nodeids'],addnet['nodeids']))
        basenet['nodes'] = numpy.concatenate((basenet['nodes'],addnet['nodes']))
        newedges = []
        newedgeweights = []
        for e in addnet['edges']:
            newe = (baseids[e[0]],e[0]+NUMNODES)
            newedges.append(newe)
            newedgeweights.append(4.0)
            newe = (e[1]+NUMNODES,baseids[e[1]])
            newedges.append(newe)
            newedgeweights.append(0.5)
        newedges = numpy.array(newedges,dtype="int32")
        newedgeweights = numpy.array(newedgeweights,dtype="float32")

        # the indices move over
        addnet['edges']+=NUMNODES
        revedges = numpy.transpose(numpy.vstack((basenet['edges'][:,1],basenet['edges'][:,0])))

        basenet['edges'] = numpy.concatenate((basenet['edges'],revedges,addnet['edges'],newedges))
        basenet['edgeweights'] = numpy.concatenate((basenet['edgeweights'],basenet['edgeweights'],addnet['edgeweights'],newedgeweights))

        return basenet

    def getgraphxys(my,gno=0):
        return my.graphxys[gno]

    def convertgraphs(my,gsrc,gtgt,values,dist=-1):
        tgtids = my.XYtoNode(my.graphxys[gtgt],gno=gsrc,distance=dist)
        v = values[tgtids]
        v[numpy.where(tgtids == -1)] = 0
        return v

    def setparcelxys(my,ids,xys):
        pidmaps = []
        for i in range(my.numgraphs):
            nodeids = my.XYtoNode(xys,gno=i)
            tmp = dict(zip(ids,nodeids))
            pidmaps.append(tmp)
        my.pidmaps = pidmaps

    def pids2nodes(my,pids):
        nodes_list = []
        for g in range(my.numgraphs):
            nodes = copy.deepcopy(pids)
            for i in range(len(pids)):
                nodes[i] = my.pidmaps[g][pids[i]]
            nodes_list.append(nodes)
        return nodes_list

    def subset(my,nodes,subset):
        newlist = []
        for g in range(my.numgraphs):
            newlist.append(nodes[g][subset])
        return newlist

    def createGraphs(my,num):
        my.numgraphs = num
        my.graphxys = [None for i in range(num)]
        _pyaccess.create_graphs(num)

    # id is an identifier for this graph
    # nodeids is a numpy array of ints that are ids
    # nodexy is a Nx2 array of floats which are the x / y coords (lat / longs)
    # edgedef is a Nx2 array where each row is an edge - the two ints identify
    #         the INDEXES of the nodes, not the nodeids
    # weights the impedances for each each - one to one mapping ot edgedef
    def createGraph(my,id,nodeids,nodexy,edgedef,weights,twoway=0):
        my.graphxys[id] = nodexy
        _pyaccess.create_graph(id,nodeids,nodexy,edgedef,weights,twoway)

    def initializePOIs(my,numcategories,maxdist,maxitems):
        _pyaccess.initialize_pois(numcategories,maxdist,maxitems)

    def initializeCategory(my,cat,latlongs):
        _pyaccess.initialize_category(cat,latlongs)

    def findNearestPOIs(my,nodeid,radius,number,category):
        return _pyaccess.find_nearest_pois(nodeid,radius,number,category)
    
    def findAllNearestPOIs(my,radius,category):
        l = _pyaccess.find_all_nearest_pois(radius,category)
        return [x if x != -1 else radius for x in l]

    def getOpenWalkscore(my,nodeid):
        return _pyaccess.get_open_walkscore(nodeid)

    def getAllOpenWalkscores(my):
        return _pyaccess.get_all_open_walkscores()

    def initializeAccVars(my,numcategories):
        for i in range(my.numgraphs):
            _pyaccess.initialize_acc_vars(i,numcategories)
    
    # this is a possible performance improvement where I presum by node
    # is not going to help much unless there's a lot of data elements though, which there aren't
    def sum_by_group(my,values, groups):
        order = numpy.argsort(groups)
        groups = groups[order]
        values = values[order]
        values.cumsum(out=values)
        index = numpy.ones(len(groups), 'bool')
        index[:-1] = groups[1:] != groups[:-1]
        values = values[index]
        groups = groups[index]
        values[1:] = values[1:] - values[:-1]
        return values, groups
    
    def initializeAccVarDirect(my,gno,cat,nodeids,accvar):
        _pyaccess.initialize_acc_var(gno,cat,nodeids,accvar)

    def initializeAccVar(my,cat,nodeids,accvar,preaggregate=0):
        if my.numgraphs == 1 and type(nodeids) <> type([]):
            nodeids = [nodeids] # allow passing node ids not as a list of lists when one graph
        for i in range(my.numgraphs):
            if preaggregate:
                tmpaccvar, tmpnodeids = my.sum_by_group(accvar, nodeids[i])
            else: tmpnodeids, tmpaccvar = nodeids[i], accvar
            _pyaccess.initialize_acc_var(i,cat,tmpnodeids,tmpaccvar)

    def XYtoNode(my,xy,distance=-1,gno=0):
        assert np.where(xy==np.nan)[0].size == 0
        return _pyaccess.xy_to_node(xy,distance,gno)

    def LatLongtoNode(my,lat,lon,gno=0,distance=-1):
        xy = numpy.array([(lon,lat)],dtype=numpy.float32)
        return my.XYtoNode(xy,gno=gno,distance=distance)[0]
    
    def getManyAggregateAccessibilityVariables(my,nodeids,radius,index,aggregation, \
																decay):
        return _pyaccess.get_many_aggregate_accessibility_variables(nodeids,radius, \
													index,aggregation,decay)

    def getAllAggregateAccessibilityVariables(my,radius,index,aggregation, \
														decay,gno=0,impno=0):
        return _pyaccess.get_all_aggregate_accessibility_variables(radius, \
													index,aggregation,decay,gno,impno)

    def getAllModelResults(my,radius,varindexes,varcoeffs,distcoeff=0.0, \
                                                asc=0.0,denom=-1.0,nestdenom=-1.0,mu=1.0,gno=0,impno=0):
        varindexes = np.array(varindexes,dtype="int32")
        varcoeffs = np.array(varcoeffs,dtype="float32")
        return _pyaccess.get_all_model_results(radius,varindexes,varcoeffs,distcoeff,asc,denom,nestdenom,mu,gno,impno)

    def getAllWeightedAverages(my,index,localradius=.5,regionalradius=3.0,minimumobservations=10,agg=1,decay=2):
        local = my.getAllAggregateAccessibilityVariables(localradius,index,agg,decay) #,gno=j)
        localcnt = my.getAllAggregateAccessibilityVariables(localradius,index,6,2) #,gno=j)
        regional = my.getAllAggregateAccessibilityVariables(regionalradius,index,agg,decay) #,gno=j)
        regionalcnt = my.getAllAggregateAccessibilityVariables(regionalradius,index,6,2) #,gno=j)
        localcnt[numpy.where(localcnt>minimumobservations)[0]] = minimumobservations
        localprop = localcnt / float(minimumobservations)
        regionalprop = 1.0-localprop
        weightedave = local*localprop+regional*regionalprop
        weightedave[numpy.where(regionalcnt<minimumobservations)[0]] = 0
        return weightedave
    
    def aggregateAccessibilityVariable(my,nid,radius,index,aggregation,decay,gno=0,impno=0):
        return _pyaccess.aggregate_accessibility_variable(nid,radius, \
													index,aggregation,decay,gno,impno)

    def computeDesignVariable(my,nid,radius,typ,gno=0):
		return _pyaccess.compute_design_variable(nid,radius,typ,gno)
    
    def computeAllDesignVariables(my,radius,typ,gno=0):
        return _pyaccess.compute_all_design_variables(radius,typ,gno)

    def precomputeRange(my,radius,gno=0):
        return _pyaccess.precompute_range(radius,gno)

    def sampleAllNodesinRange(my,samplesize,radius,gno=0,impno=0):
        return _pyaccess.sample_all_nodes_in_range(samplesize,radius,gno,impno)

    def sampleManyNodesinRange(my,nodeids,samplesize,radius,skipchoice,gno=0,impno=0):
        return _pyaccess.sample_many_nodes_in_range(nodeids,samplesize,radius,skipchoice,gno,impno)

    def getNodesinRange(my,nodeid,radius,gno=0,impno=0):
        return _pyaccess.get_nodes_in_range(nodeid,radius,gno,impno)

    def getGraphIDS(my,gno=0):
        return _pyaccess.get_node_ids(gno)

    def loadFromFile(my,filename):
        my.graphxys = [None for i in range(my.numgraphs)]
        for g in range(my.numgraphs):
            print "Loading network from file %s" % (filename%g)
            _pyaccess.load_from_file(filename%g,g)
            my.graphxys[g] = numpy.transpose(_pyaccess.get_node_xys(g))

    def saveToFile(my,filename):
        for g in range(my.numgraphs):
            _pyaccess.save_to_file(filename%g,g)
    
    def saveToCSV(my,filename):
        for g in range(my.numgraphs):
            _pyaccess.save_to_csv(filename%g,g)

    def numNodes(my,gno):
        return _pyaccess.num_nodes(gno)

    def Distance(my,srcnode,destnode,gno=0,impno=0):
        return _pyaccess.route_distance(srcnode,destnode,gno,impno)